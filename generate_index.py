#!/usr/bin/env python3
"""Generate the static index page for The Signal from local episode files."""

import glob
import html
import os
import re
import subprocess
from datetime import datetime

BASE_DIR = "/agent/work/podcast"
EPISODES_DIR = f"{BASE_DIR}/episodes"
SCRIPTS_DIR = f"{BASE_DIR}/scripts"
INDEX_PATH = f"{BASE_DIR}/index.html"
EPISODE_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.mp3$")


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
    episodes = sorted(
        (
            path
            for path in glob.glob(os.path.join(EPISODES_DIR, "*.mp3"))
            if EPISODE_FILENAME_RE.match(os.path.basename(path))
        ),
        reverse=True,
    )
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
        .subscribe h2 {{ font-size: 1.1rem; margin-bottom: 0.75rem; }}
        .subscribe-buttons {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem; }}
        .subscribe-buttons a {{ display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1rem; background: #21262d; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; text-decoration: none; font-size: 0.9rem; transition: background 0.15s; }}
        .subscribe-buttons a:hover {{ background: #30363d; }}
        .subscribe-buttons svg {{ width: 18px; height: 18px; flex-shrink: 0; }}
        .subscribe a, .footer a, .footer-links a {{ color: #58a6ff; }}
        .footer-links {{ margin-top: 1rem; text-align: center; color: #8b949e; font-size: 0.85rem; }}
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

        <div class="subscribe">
            <h2>Subscribe</h2>
            <div class="subscribe-buttons">
                <a href="https://podcasts.apple.com/us/podcast/the-signal/id1887760992">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 3.5a4 4 0 0 1 1.031 7.868c.278.552.469 1.26.469 2.132 0 .87-.244 1.64-.512 2.28-.268.64-.612 1.22-.612 1.22l-.376-.001c0 0-.344-.58-.612-1.22-.268-.64-.512-1.41-.512-2.28 0-.872.191-1.58.469-2.132A4 4 0 0 1 12 5.5zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/></svg>
                    Apple Podcasts
                </a>
                <a href="https://open.spotify.com/show/4gHudL3K8cnec5bgRlsjzZ">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm4.586 14.424a.622.622 0 0 1-.857.207c-2.348-1.435-5.304-1.76-8.786-.964a.623.623 0 0 1-.277-1.215c3.809-.87 7.076-.496 9.713 1.115a.623.623 0 0 1 .207.857zm1.224-2.719a.78.78 0 0 1-1.072.257c-2.687-1.652-6.785-2.131-9.965-1.166a.78.78 0 0 1-.452-1.493c3.632-1.102 8.147-.568 11.234 1.33a.78.78 0 0 1 .255 1.072zm.105-2.835C14.692 8.95 9.375 8.775 6.297 9.71a.934.934 0 1 1-.542-1.79c3.533-1.072 9.404-.865 13.115 1.338a.934.934 0 0 1-1.045 1.547l.09-.025z"/></svg>
                    Spotify
                </a>
                <a href="https://overcast.fm/itunes1887760992">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 2a8 8 0 1 1 0 16 8 8 0 0 1 0-16zm0 3a5 5 0 0 0-3.5 8.573l1.5-5.073h4l1.5 5.073A5 5 0 0 0 12 7z"/></svg>
                    Overcast
                </a>
                <a href="#" id="rss-copy" onclick="navigator.clipboard.writeText('https://warmidris.github.io/the-signal/feed/feed.xml').then(function(){{var b=document.getElementById('rss-copy');b.dataset.orig=b.innerHTML;b.innerHTML='<svg viewBox=&quot;0 0 24 24&quot; fill=&quot;currentColor&quot; style=&quot;width:18px;height:18px&quot;><path d=&quot;M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z&quot;/></svg> Copied!';setTimeout(function(){{b.innerHTML=b.dataset.orig}},2000)}});return false">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6.18 15.64a2.18 2.18 0 0 1 2.18 2.18C8.36 19 7.38 20 6.18 20 5 20 4 19 4 17.82a2.18 2.18 0 0 1 2.18-2.18zM4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27V4.44zm0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93V10.1z"/></svg>
                    RSS
                </a>
            </div>
        </div>

{chr(10).join(episode_html)}

        <div class="footer-links">
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
