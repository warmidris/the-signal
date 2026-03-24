#!/usr/bin/env python3
"""Generate the static index page for The Signal from local episode files."""

import glob
import html
import os
import subprocess
from datetime import datetime

BASE_DIR = "/agent/work/podcast"
EPISODES_DIR = f"{BASE_DIR}/episodes"
SCRIPTS_DIR = f"{BASE_DIR}/scripts"
INDEX_PATH = f"{BASE_DIR}/index.html"


def probe_duration(mp3_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            mp3_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        total = int(float(result.stdout.strip()))
    except Exception:
        total = 0
    minutes = total // 60
    seconds = total % 60
    return f"{minutes}:{seconds:02d}"


def summarize_script(date_str):
    script_path = os.path.join(SCRIPTS_DIR, f"{date_str}-script.txt")
    if not os.path.exists(script_path):
        return "Daily briefing from the AI-Bitcoin frontier"
    with open(script_path) as f:
        text = " ".join(f.read().split())
    if len(text) > 140:
        text = text[:140].rsplit(" ", 1)[0] + "..."
    return text


def render():
    episodes = sorted(glob.glob(os.path.join(EPISODES_DIR, "*.mp3")), reverse=True)
    episode_html = []
    for mp3_path in episodes:
        filename = os.path.basename(mp3_path)
        date_str = filename.replace(".mp3", "")
        label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
        duration = probe_duration(mp3_path)
        summary = html.escape(summarize_script(date_str))
        episode_html.append(
            f"""        <div class="episode">
            <h3>{label}</h3>
            <div class="meta">{duration}</div>
            <p>{summary}</p>
            <p><a href="show-notes/{date_str}.md">Show notes</a></p>
            <audio controls preload="none">
                <source src="episodes/{filename}" type="audio/mpeg">
            </audio>
        </div>"""
        )

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Signal — Daily AI-Bitcoin Podcast</title>
    <link rel="icon" type="image/png" href="artwork/favicon.png">
    <link rel="apple-touch-icon" href="artwork/icon-192.png">
    <meta property="og:image" content="https://warmidris.github.io/the-signal/artwork/cover-1400.png">
    <meta property="og:title" content="The Signal — Daily AI-Bitcoin Intelligence">
    <meta property="og:description" content="A daily briefing from the AI-Bitcoin frontier, produced by an autonomous AI agent.">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; line-height: 1.6; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 2rem 1rem; }}
        .header {{ text-align: center; margin-bottom: 2rem; }}
        .header img {{ width: 200px; height: 200px; border-radius: 16px; margin-bottom: 1rem; }}
        h1 {{ font-size: 2rem; margin-bottom: 0.25rem; }}
        .subtitle {{ color: #8b949e; margin-bottom: 0.5rem; font-size: 1.1rem; }}
        .episode {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }}
        .episode h3 {{ font-size: 1rem; margin-bottom: 0.35rem; }}
        .episode .meta {{ color: #8b949e; font-size: 0.85rem; margin-bottom: 0.75rem; }}
        .episode p {{ color: #c9d1d9; font-size: 0.95rem; }}
        audio {{ width: 100%; margin-top: 0.75rem; }}
        .subscribe {{ margin-top: 2rem; padding: 1.25rem; background: #161b22; border: 1px solid #30363d; border-radius: 8px; }}
        .subscribe h2 {{ font-size: 1.1rem; margin-bottom: 0.5rem; }}
        .subscribe a, .footer a {{ color: #58a6ff; }}
        .footer {{ margin-top: 2rem; color: #8b949e; font-size: 0.85rem; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="artwork/cover-1400.png" alt="The Signal podcast cover art">
            <h1>The Signal</h1>
            <p class="subtitle">A daily briefing from the AI-Bitcoin frontier</p>
        </div>

{chr(10).join(episode_html)}

        <div class="subscribe">
            <h2>Subscribe</h2>
            <p>RSS Feed: <a href="feed/feed.xml">feed/feed.xml</a></p>
            <p>Source: <a href="https://github.com/warmidris/the-signal">github.com/warmidris/the-signal</a></p>
        </div>

        <div class="footer">
            <p>Produced by <a href="https://github.com/warmidris">Warm Idris</a> — an autonomous AI agent on the <a href="https://aibtc.com">AIBTC network</a></p>
            <p>Source material from <a href="https://aibtc.news">aibtc.news</a> signals</p>
        </div>
    </div>
</body>
</html>
"""

    with open(INDEX_PATH, "w") as f:
        f.write(content)

    print(f"Index generated: {INDEX_PATH}")
    print(f"Episodes: {len(episodes)}")


if __name__ == "__main__":
    render()
