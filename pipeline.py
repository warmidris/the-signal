#!/usr/bin/env python3
"""
The Signal — Automated podcast pipeline.

Usage:
    python3 pipeline.py [YYYY-MM-DD]

Fetches signals from aibtc.news, generates a podcast script using Claude CLI,
converts to audio via edge-tts, and updates the site/feed.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from openai_tts import generate_audio_file as generate_openai_audio_file

BASE_DIR = "/agent/work/podcast"
SCRIPTS_DIR = f"{BASE_DIR}/scripts"
EPISODES_DIR = f"{BASE_DIR}/episodes"
SHOW_NOTES_DIR = f"{BASE_DIR}/show-notes"
FEED_DIR = f"{BASE_DIR}/feed"

AUDIO_BACKEND = os.environ.get("SIGNAL_AUDIO_BACKEND", "openai")
VOICE = os.environ.get("SIGNAL_EDGE_VOICE", "en-US-AndrewNeural")
RATE = os.environ.get("SIGNAL_EDGE_RATE", "+5%")
OPENAI_MODEL = os.environ.get("SIGNAL_OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_VOICE = os.environ.get("SIGNAL_OPENAI_TTS_VOICE", "cedar")
OPENAI_ENV_FILE = os.environ.get("SIGNAL_OPENAI_ENV_FILE", "/agent/identity/openai.env")
OPENAI_INSTRUCTIONS = os.environ.get(
    "SIGNAL_OPENAI_TTS_INSTRUCTIONS",
    (
        "Speak like a confident podcast host. Warm, clear, and conversational. "
        "Keep a steady pace, slight smile in the voice, and crisp enunciation for numbers."
    ),
)
CLAUDE_TIMEOUT_SECONDS = int(os.environ.get("SIGNAL_CLAUDE_TIMEOUT_SECONDS", "600"))
MIN_SIGNALS_PER_EPISODE = 3
PUBLISHABLE_STATUSES = {"approved", "brief_included"}
SIGNALS_FETCH_LIMIT = int(os.environ.get("SIGNAL_FETCH_LIMIT", "1000"))


def format_utc_timestamp(dt):
    """Format a UTC datetime for APIs that expect an RFC3339 Z suffix."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_signal_timestamp(value):
    """Parse RFC3339 timestamps from aibtc.news into aware UTC datetimes."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def resolve_author_name(btc_address):
    """Resolve a signal BTC address to a display name when possible."""
    if not btc_address:
        return "Unknown correspondent"
    url = f"https://aibtc.com/api/agents/{btc_address}"
    try:
        data = fetch_json(url)
        agent = data.get("agent", {})
        return agent.get("displayName") or agent.get("owner") or btc_address
    except Exception:
        return btc_address


def fetch_json(url):
    result = subprocess.run(
        ["curl", "-sS", "-A", "Idris-Podcast/1.0", url],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def fetch_signals(target_date_str):
    """Fetch publishable signals from the last published episode through target_date UTC."""
    print(f"[1/5] Fetching signals for {target_date_str}...")

    target_day = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    window_end = target_day + timedelta(days=1)

    latest_episode_date = None
    if os.path.isdir(EPISODES_DIR):
        for filename in os.listdir(EPISODES_DIR):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.mp3", filename):
                continue
            date_part = filename[:-4]
            if date_part >= target_date_str:
                continue
            latest_episode_date = max(latest_episode_date or date_part, date_part)

    if latest_episode_date:
        window_start = (
            datetime.strptime(latest_episode_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            + timedelta(days=1)
        )
    else:
        window_start = target_day

    data = fetch_json(
        f"https://aibtc.news/api/signals?limit={SIGNALS_FETCH_LIMIT}&since={format_utc_timestamp(window_start)}"
    )
    all_signals = data.get("signals", [])
    publishable = [
        s for s in all_signals
        if s.get("status") in PUBLISHABLE_STATUSES
        and s.get("content")
        and (ts := parse_signal_timestamp(s.get("timestamp")))
        and window_start <= ts < window_end
    ]
    publishable.sort(key=lambda s: s["timestamp"])

    signals_file = f"{SCRIPTS_DIR}/{target_date_str}-signals.json"
    with open(signals_file, "w") as f:
        json.dump({
            "targetDate": target_date_str,
            "windowStart": window_start.strftime("%Y-%m-%d"),
            "windowEnd": target_day.strftime("%Y-%m-%d"),
            "publishableStatuses": sorted(PUBLISHABLE_STATUSES),
            "signals": publishable,
        }, f, indent=2)

    print(
        f"  Window: {window_start.strftime('%Y-%m-%d')} through {target_day.strftime('%Y-%m-%d')} UTC"
    )
    print(f"  Found {len(publishable)} publishable signals ({', '.join(sorted(PUBLISHABLE_STATUSES))})")

    return publishable, window_start.strftime("%Y-%m-%d"), target_day.strftime("%Y-%m-%d")


def generate_script(date_str, signals, window_start_str, window_end_str):
    """Generate podcast script using Claude CLI."""
    print(f"[2/4] Generating script...")

    script_file = f"{SCRIPTS_DIR}/{date_str}-script.txt"
    if os.path.exists(script_file):
        print(f"  Script already exists: {script_file}")
        return script_file

    signal_summaries = []
    for s in signals:
        signal_summaries.append(
            f"[{s['beat']}] {s['headline']}\n{s['content']}"
        )
    signals_text = "\n\n---\n\n".join(signal_summaries)
    source_section = f"""Here are the approved signals from aibtc.news published between {window_start_str} and {window_end_str} UTC:

{signals_text}"""
    extra_instruction = (
        "- Synthesize these into a cohesive ~7-minute script (800-1100 words)\n"
        "- Include specific numbers from the signals — don't be vague\n"
        "- Group related signals into themed segments\n"
        "- Add editorial commentary that connects dots between signals\n"
    )

    prompt = f"""Write a podcast script for "The Signal", a daily briefing from the AI-Bitcoin frontier, for {date_str}.

{source_section}

INSTRUCTIONS:
- Open with "Welcome to The Signal, your daily briefing from the AI-Bitcoin frontier. It's [date]. Let's get into it."
- Do NOT mention the signal window dates or UTC timestamps in the script.
- Close with "That's your signal for [date]." followed by a brief forward-looking statement.
- Then end with: "If you find this useful, share it with someone who should be paying attention. And if you're an AI agent or developer who wants to be part of the story — register at aibtc.com, claim a beat, and start submitting signals. I'll see you tomorrow."
- The tone should be enthusiastic about Bitcoin, grounded in "fix the money, fix the world" energy
- Have genuine character — this is a host who believes in sound money, not a neutral news reader
{extra_instruction}- If you reference aibtc.news, do so accurately and explicitly
- Do NOT use bullet points or headers — this is spoken word
- Do NOT use abbreviations that sound weird when read aloud (spell out "versus", etc.)
- Be careful with numbers: write them as words for speech ("seventy thousand" not "70,000")
- Output ONLY the script text, nothing else"""

    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=CLAUDE_TIMEOUT_SECONDS,
    )

    if result.returncode != 0:
        print(f"  Error generating script: {result.stderr[:200]}")
        return None

    script_text = result.stdout.strip()
    if not script_text:
        print("  Error generating script: empty response")
        return None

    # Strip any preamble Claude might add before the actual script
    for marker in ["---\n\n", "---\r\n\r\n"]:
        if marker in script_text[:100]:
            script_text = script_text.split(marker, 1)[1]
    script_text = re.sub(r"^Here'?s the script:?\s*", "", script_text, flags=re.IGNORECASE)

    with open(script_file, "w") as f:
        f.write(script_text)

    word_count = len(script_text.split())
    print(f"  Script written: {word_count} words")
    return script_file


def generate_show_notes(date_str, signals, window_start_str, window_end_str):
    """Generate markdown show notes with source and correspondent credits."""
    os.makedirs(SHOW_NOTES_DIR, exist_ok=True)
    notes_file = f"{SHOW_NOTES_DIR}/{date_str}.md"

    lines = [
        f"# The Signal — {date_str}",
        "",
        "Source material: [aibtc.news](https://aibtc.news)",
        f"Coverage window: {window_start_str} through {window_end_str} UTC",
        "",
        "## Signals Covered",
        "",
    ]

    for signal in signals:
        headline = signal.get("headline") or "Untitled signal"
        beat = signal.get("beat") or "Unknown beat"
        btc_address = signal.get("btcAddress")
        author_name = resolve_author_name(btc_address)
        lines.append(f"- **{headline}**")
        lines.append(f"  Beat: {beat}")
        lines.append(f"  Correspondent: {author_name}")
        if btc_address:
            lines.append(f"  BTC address: `{btc_address}`")
        if signal.get("sources"):
            lines.append("  Sources:")
            for source in signal["sources"]:
                title = source.get("title") or source.get("url") or "Untitled source"
                url = source.get("url") or ""
                lines.append(f"  - [{title}]({url})")
        lines.append("")

    lines.extend([
        "## Get Involved",
        "",
        "- **Listen and share** — If you found this useful, pass it along to someone who should be paying attention.",
        "- **Become a correspondent** — If you're an AI agent or developer, register at [aibtc.com](https://aibtc.com), claim a beat, and start submitting signals.",
        "- **Subscribe** — [RSS Feed](https://warmidris.github.io/the-signal/feed/feed.xml) | [GitHub](https://github.com/warmidris/the-signal)",
        "",
        "## Credits",
        "",
        "- Produced by [Warm Idris](https://github.com/warmidris)",
        "- Reporting and source discovery by [aibtc.news](https://aibtc.news) correspondents credited above",
        "",
    ])

    with open(notes_file, "w") as f:
        f.write("\n".join(lines))

    print(f"  Show notes: {notes_file}")
    return notes_file


def generate_audio(date_str, script_file):
    """Convert script to audio via configured backend."""
    print(f"[4/5] Generating audio...")

    mp3_file = f"{EPISODES_DIR}/{date_str}.mp3"
    if os.path.exists(mp3_file):
        print(f"  Audio already exists: {mp3_file}")
        return mp3_file

    backend_used = AUDIO_BACKEND
    try:
        if AUDIO_BACKEND == "openai":
            result = generate_openai_audio_file(
                script_file,
                mp3_file,
                env_file=OPENAI_ENV_FILE,
                model=OPENAI_MODEL,
                voice=OPENAI_VOICE,
                instructions=OPENAI_INSTRUCTIONS,
            )
            print(
                f"  OpenAI TTS: model={result['model']}, voice={result['voice']}, "
                f"chars={result['characters']}, chunks={result['chunks']}"
            )
        elif AUDIO_BACKEND == "edge":
            result = subprocess.run(
                ["edge-tts", "--voice", VOICE, "--rate", RATE,
                 "--file", script_file, "--write-media", mp3_file],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                print(f"  Error generating audio: {result.stderr[:200]}")
                return None
        else:
            print(f"  Error generating audio: unknown backend '{AUDIO_BACKEND}'")
            return None
    except Exception as exc:
        if AUDIO_BACKEND != "openai":
            print(f"  Error generating audio: {exc}")
            return None

        print(f"  OpenAI TTS failed, falling back to edge-tts: {exc}")
        backend_used = "edge"
        result = subprocess.run(
            ["edge-tts", "--voice", VOICE, "--rate", RATE,
             "--file", script_file, "--write-media", mp3_file],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            print(f"  Error generating audio: {result.stderr[:200]}")
            return None

    # Get duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", mp3_file],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip())
    minutes = int(duration) // 60
    seconds = int(duration) % 60
    size_kb = os.path.getsize(mp3_file) // 1024

    print(f"  Audio ({backend_used}): {minutes}:{seconds:02d}, {size_kb}KB")
    return mp3_file


def update_site():
    """Regenerate the RSS feed and static index."""
    print(f"[5/5] Updating RSS feed...")
    result = subprocess.run(
        ["python3", f"{BASE_DIR}/generate_feed.py"],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    print(f"  {result.stdout.strip()}")

    index_result = subprocess.run(
        ["python3", f"{BASE_DIR}/generate_index.py"],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    print(f"  {index_result.stdout.strip()}")


def post_episode_tweet(date_str, signals):
    """Post a tweet announcing the new episode."""
    print(f"[7/7] Posting to X...")
    try:
        # Pick top 2-3 beats for highlights
        beats = []
        for s in signals:
            beat = s.get("beat", "")
            if beat and beat not in beats:
                beats.append(beat)
            if len(beats) >= 3:
                break
        highlights = ", ".join(beats) if beats else "the latest from the AI-Bitcoin frontier"

        listen_url = "https://podcasts.apple.com/us/podcast/the-signal/id1887760992"

        tweet = (
            f"New episode of The Signal — {date_str}\n\n"
            f"Today's briefing covers: {highlights}\n\n"
            f"Listen: {listen_url}\n\n"
            f"Source: @aibtcdev correspondents"
        )

        result = subprocess.run(
            ["python3", "/agent/bin/post_tweet.py", tweet],
            capture_output=True, text=True, timeout=30,
        )
        print(f"  {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"  Tweet failed: {result.stderr[:200]}")
    except Exception as exc:
        print(f"  Tweet failed: {exc}")


def publish_to_github(date_str):
    """Commit new episode files and push to GitHub Pages."""
    print(f"[6/7] Publishing to GitHub...")
    try:
        subprocess.run(
            ["git", "add", "episodes/", "feed/", "scripts/", "show-notes/", "index.html"],
            cwd=BASE_DIR, capture_output=True, text=True, check=True,
        )
        # Check if there's anything to commit
        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=BASE_DIR, capture_output=True,
        )
        if status.returncode == 0:
            print("  Nothing new to commit.")
            return
        subprocess.run(
            ["git", "commit", "-m", f"Publish {date_str} episode"],
            cwd=BASE_DIR, capture_output=True, text=True, check=True,
        )
        result = subprocess.run(
            ["git", "push"],
            cwd=BASE_DIR, capture_output=True, text=True, check=True,
        )
        print(f"  Pushed to GitHub.")
    except subprocess.CalledProcessError as exc:
        print(f"  Git publish failed: {exc.stderr[:200] if exc.stderr else exc}")


def main():
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        utc_now = datetime.now(timezone.utc)
        target_day = utc_now.date() - timedelta(days=1)
        date_str = target_day.strftime("%Y-%m-%d")

    print(f"=== The Signal — Pipeline for {date_str} ===\n")

    # Step 1: Fetch
    signals, window_start_str, window_end_str = fetch_signals(date_str)
    if len(signals) < MIN_SIGNALS_PER_EPISODE:
        print(
            f"Only {len(signals)} approved signals since the last episode. "
            f"Minimum is {MIN_SIGNALS_PER_EPISODE}. Skipping today's episode."
        )
        return 0

    # Step 2: Script
    script_file = generate_script(date_str, signals, window_start_str, window_end_str)
    if not script_file:
        print("Script generation failed. Aborting.")
        return 1

    # Step 3: Audio
    print(f"[3/5] Generating show notes...")
    generate_show_notes(date_str, signals, window_start_str, window_end_str)

    # Step 4: Audio
    mp3_file = generate_audio(date_str, script_file)
    if not mp3_file:
        print("Audio generation failed. Aborting.")
        return 1

    # Step 4: Feed
    update_site()

    # Step 6: Commit and push to GitHub Pages
    publish_to_github(date_str)

    # Step 7: Post to X
    post_episode_tweet(date_str, signals)

    print(f"\nDone! Episode: {mp3_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
