#!/usr/bin/env python3
"""
The Signal — Automated podcast pipeline.

Usage:
    python3 pipeline.py [YYYY-MM-DD]

Fetches signals from aibtc.news, generates a podcast script using Claude CLI,
converts to audio via edge-tts, and updates the RSS feed.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = "/agent/work/podcast"
SCRIPTS_DIR = f"{BASE_DIR}/scripts"
EPISODES_DIR = f"{BASE_DIR}/episodes"

VOICE = "en-US-AndrewNeural"
RATE = "+5%"


def fetch_signals(date_str):
    """Fetch approved signals for a given date."""
    print(f"[1/4] Fetching signals for {date_str}...")
    result = subprocess.run(
        ["python3", f"{BASE_DIR}/fetch.py", date_str],
        capture_output=True, text=True, cwd=BASE_DIR
    )

    signals_file = f"{SCRIPTS_DIR}/{date_str}-signals.json"
    if not os.path.exists(signals_file):
        print(f"Error: No signals file created for {date_str}")
        return None

    with open(signals_file) as f:
        data = json.load(f)

    approved = [s for s in data["signals"] if s["status"] == "approved"]
    print(f"  Found {len(data['signals'])} total, {len(approved)} approved")

    if len(approved) < 3:
        print(f"  Warning: Only {len(approved)} approved signals — episode may be thin")

    return approved


def generate_script(date_str, signals):
    """Generate podcast script using Claude CLI."""
    print(f"[2/4] Generating script...")

    script_file = f"{SCRIPTS_DIR}/{date_str}-script.txt"
    if os.path.exists(script_file):
        print(f"  Script already exists: {script_file}")
        return script_file

    # Build prompt for Claude
    signal_summaries = []
    for s in signals:
        signal_summaries.append(
            f"[{s['beat']}] {s['headline']}\n{s['content']}"
        )

    signals_text = "\n\n---\n\n".join(signal_summaries)

    prompt = f"""Write a podcast script for "The Signal", a daily briefing from the AI-Bitcoin frontier, for {date_str}.

Here are today's approved signals from aibtc.news:

{signals_text}

INSTRUCTIONS:
- Synthesize these into a cohesive ~7-minute script (800-1100 words)
- Open with "Welcome to The Signal, your daily briefing from the AI-Bitcoin frontier. It's [date]. Let's get into it."
- Close with "That's your signal for [date]." followed by a brief forward-looking statement and "I'll see you tomorrow."
- The tone should be enthusiastic about Bitcoin, grounded in "fix the money, fix the world" energy
- Have genuine character — this is a host who believes in sound money, not a neutral news reader
- Include specific numbers from the signals — don't be vague
- Group related signals into themed segments
- Add editorial commentary that connects dots between signals
- Do NOT use bullet points or headers — this is spoken word
- Do NOT use abbreviations that sound weird when read aloud (spell out "versus", etc.)
- Be careful with numbers: write them as words for speech ("seventy thousand" not "70,000")
- Output ONLY the script text, nothing else"""

    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        print(f"  Error generating script: {result.stderr[:200]}")
        return None

    script_text = result.stdout.strip()
    with open(script_file, "w") as f:
        f.write(script_text)

    word_count = len(script_text.split())
    print(f"  Script written: {word_count} words")
    return script_file


def generate_audio(date_str, script_file):
    """Convert script to audio via edge-tts."""
    print(f"[3/4] Generating audio...")

    mp3_file = f"{EPISODES_DIR}/{date_str}.mp3"
    if os.path.exists(mp3_file):
        print(f"  Audio already exists: {mp3_file}")
        return mp3_file

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

    print(f"  Audio: {minutes}:{seconds:02d}, {size_kb}KB")
    return mp3_file


def update_feed():
    """Regenerate the RSS feed."""
    print(f"[4/4] Updating RSS feed...")
    result = subprocess.run(
        ["python3", f"{BASE_DIR}/generate_feed.py"],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    print(f"  {result.stdout.strip()}")


def main():
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"=== The Signal — Pipeline for {date_str} ===\n")

    # Step 1: Fetch
    signals = fetch_signals(date_str)
    if not signals:
        print("No approved signals found. Aborting.")
        return 1

    # Step 2: Script
    script_file = generate_script(date_str, signals)
    if not script_file:
        print("Script generation failed. Aborting.")
        return 1

    # Step 3: Audio
    mp3_file = generate_audio(date_str, script_file)
    if not mp3_file:
        print("Audio generation failed. Aborting.")
        return 1

    # Step 4: Feed
    update_feed()

    print(f"\nDone! Episode: {mp3_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
