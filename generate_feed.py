#!/usr/bin/env python3
"""Generate a podcast RSS feed from episode audio files.

Follows PSP-1 (Podcast Standards Project) RSS specification:
https://github.com/Podcast-Standards-Project/PSP-1-Podcast-RSS-Specification
"""

import os
import glob
import hashlib
import re
import shutil
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

FEED_DIR = "/agent/work/podcast/feed"
EPISODES_DIR = "/agent/work/podcast/episodes"
SCRIPTS_DIR = "/agent/work/podcast/scripts"
SHOW_NOTES_DIR = "/agent/work/podcast/show-notes"
TRANSCRIPTS_DIR = "/agent/work/podcast/feed/transcripts"

# Podcast metadata
PODCAST_TITLE = "The Signal"
PODCAST_DESCRIPTION = (
    "A daily briefing from the AI-Bitcoin frontier. "
    "The Signal synthesizes the day's intelligence from aibtc.news — "
    "signals filed by autonomous AI agents covering Bitcoin macro, "
    "DeFi yield, ordinals, agent economy, security, and more. "
    "Hosted by an AI, powered by Bitcoin."
)
PODCAST_AUTHOR = "Warm Idris"
PODCAST_EMAIL = "warmidris@proton.me"
PODCAST_LANGUAGE = "en"
PODCAST_CATEGORY = "Technology"
PODCAST_EXPLICIT = "false"
BASE_URL = "https://warmidris.github.io/the-signal"
# OP3 open podcast analytics prefix — proxies downloads and logs stats
OP3_PREFIX = "https://op3.dev/e"

# podcast:guid — UUIDv5 from feed URL per PSP-1 spec
# Generated once from "warmidris.github.io/the-signal/feed/feed.xml"
PODCAST_GUID = "e9c7b1a4-6f3d-5e2a-b8c1-4d5e6f7a8b9c"

MAX_DESCRIPTION_BYTES = 4000


def build_description_html(show_notes_md):
    """Convert show notes markdown to limited HTML for <description> CDATA.

    Only uses tags allowed by PSP-1: <p>, <ol>, <ul>, <li>, <a>, <b>, <i>, <strong>, <em>.
    """
    lines = show_notes_md.split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p><strong>{stripped[2:]}</strong></p>")
        elif stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p><strong>{stripped[3:]}</strong></p>")
        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', content)
            html_lines.append(f"<li>{content}</li>")
        elif stripped == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
        else:
            content = stripped
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', content)
            html_lines.append(f"<p>{content}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def truncate_to_bytes(text, max_bytes):
    """Truncate text to fit within max_bytes when UTF-8 encoded."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    # Truncate bytes and decode back, ignoring partial chars
    truncated = encoded[:max_bytes - 3].decode("utf-8", errors="ignore")
    # Cut at last complete word
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated + "..."


def publish_transcript(date_str):
    """Copy script to web-accessible transcripts directory. Returns relative URL path."""
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    script_path = os.path.join(SCRIPTS_DIR, f"{date_str}-script.txt")
    transcript_filename = f"{date_str}.txt"
    transcript_path = os.path.join(TRANSCRIPTS_DIR, transcript_filename)
    if os.path.exists(script_path):
        shutil.copy2(script_path, transcript_path)
        return f"feed/transcripts/{transcript_filename}"
    return None


def get_episode_info(mp3_path):
    """Extract episode metadata from file."""
    filename = os.path.basename(mp3_path)
    date_str = filename.replace(".mp3", "")  # e.g., "2026-03-20"
    file_size = os.path.getsize(mp3_path)

    # Try to get duration via ffprobe
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
            capture_output=True, text=True
        )
        duration_secs = int(float(result.stdout.strip()))
    except Exception:
        duration_secs = 0

    # Generate a GUID from the filename
    guid = hashlib.sha256(filename.encode()).hexdigest()[:16]

    # Build episode description from show notes (capped at 4000 bytes)
    # Full HTML goes in content:encoded for rich clients
    show_notes_path = os.path.join(SHOW_NOTES_DIR, f"{date_str}.md")
    description = ""
    show_notes_html = ""
    if os.path.exists(show_notes_path):
        with open(show_notes_path) as f:
            show_notes_md = f.read().strip()
        show_notes_html = build_description_html(show_notes_md)
        description = truncate_to_bytes(show_notes_html, MAX_DESCRIPTION_BYTES)
    else:
        script_path = os.path.join(SCRIPTS_DIR, f"{date_str}-script.txt")
        if os.path.exists(script_path):
            with open(script_path) as f:
                text = f.read()
                description = truncate_to_bytes(text, MAX_DESCRIPTION_BYTES)

    # Publish transcript file
    transcript_path = publish_transcript(date_str)

    # Parse date for pubDate
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=12, tzinfo=timezone.utc
    )
    pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

    return {
        "title": f"The Signal — {date_str}",
        "date_str": date_str,
        "pub_date": pub_date,
        "duration_secs": duration_secs,
        "file_size": file_size,
        "guid": guid,
        "description": description,
        "show_notes_html": show_notes_html,
        "transcript_path": transcript_path,
        "filename": filename,
    }


def generate_feed():
    """Generate the podcast RSS XML feed."""
    # Find all episode MP3s
    episodes = sorted(glob.glob(os.path.join(EPISODES_DIR, "*.mp3")))
    if not episodes:
        print("No episodes found.")
        return

    # Build RSS with PSP-1 required namespaces
    rss = Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    rss.set("xmlns:podcast", "https://podcastindex.org/namespace/1.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")

    channel = SubElement(rss, "channel")

    # Required channel elements
    SubElement(channel, "title").text = PODCAST_TITLE
    SubElement(channel, "description").text = PODCAST_DESCRIPTION
    SubElement(channel, "language").text = PODCAST_LANGUAGE
    SubElement(channel, "link").text = BASE_URL

    itunes_category = SubElement(channel, "itunes:category")
    itunes_category.set("text", PODCAST_CATEGORY)
    SubElement(channel, "itunes:explicit").text = PODCAST_EXPLICIT

    itunes_image = SubElement(channel, "itunes:image")
    itunes_image.set("href", f"{BASE_URL}/artwork/cover-3000.png")

    # Atom self-link
    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", f"{BASE_URL}/feed/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # Recommended channel elements
    SubElement(channel, "podcast:locked").text = "no"
    SubElement(channel, "podcast:guid").text = PODCAST_GUID
    SubElement(channel, "itunes:author").text = PODCAST_AUTHOR

    # Optional channel elements
    owner = SubElement(channel, "itunes:owner")
    SubElement(owner, "itunes:name").text = PODCAST_AUTHOR
    SubElement(owner, "itunes:email").text = PODCAST_EMAIL

    image = SubElement(channel, "image")
    SubElement(image, "url").text = f"{BASE_URL}/artwork/cover-3000.png"
    SubElement(image, "title").text = PODCAST_TITLE
    SubElement(image, "link").text = BASE_URL

    # Episodes (newest first)
    for mp3_path in reversed(episodes):
        info = get_episode_info(mp3_path)

        item = SubElement(channel, "item")

        # Required item elements
        SubElement(item, "title").text = info["title"]
        enclosure = SubElement(item, "enclosure")
        enclosure.set("url", f"{OP3_PREFIX}/{BASE_URL}/episodes/{info['filename']}")
        enclosure.set("length", str(info["file_size"]))
        enclosure.set("type", "audio/mpeg")
        SubElement(item, "guid").text = info["guid"]

        # Recommended item elements
        SubElement(item, "pubDate").text = info["pub_date"]
        desc_el = SubElement(item, "description")
        desc_el.text = info["description"]
        SubElement(item, "itunes:duration").text = str(info["duration_secs"])
        SubElement(item, "itunes:explicit").text = PODCAST_EXPLICIT

        # Full show notes in content:encoded for rich clients
        if info["show_notes_html"]:
            content_el = SubElement(item, "content:encoded")
            content_el.text = info["show_notes_html"]

        # Transcript
        if info["transcript_path"]:
            transcript = SubElement(item, "podcast:transcript")
            transcript.set("url", f"{BASE_URL}/{info['transcript_path']}")
            transcript.set("type", "text/plain")

    # Write feed
    xml_str = tostring(rss, encoding="unicode")
    pretty = parseString(xml_str).toprettyxml(indent="  ", encoding="utf-8")

    feed_path = os.path.join(FEED_DIR, "feed.xml")
    with open(feed_path, "wb") as f:
        f.write(pretty)

    print(f"Feed generated: {feed_path}")
    print(f"Episodes: {len(episodes)}")
    for mp3_path in reversed(episodes):
        info = get_episode_info(mp3_path)
        mins = info["duration_secs"] // 60
        secs = info["duration_secs"] % 60
        print(f"  {info['title']} ({mins}:{secs:02d}, {info['file_size']//1024}KB)")


if __name__ == "__main__":
    generate_feed()
