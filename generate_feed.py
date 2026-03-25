#!/usr/bin/env python3
"""Generate a podcast RSS feed from episode audio files."""

import os
import glob
import hashlib
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

FEED_DIR = "/agent/work/podcast/feed"
EPISODES_DIR = "/agent/work/podcast/episodes"
SCRIPTS_DIR = "/agent/work/podcast/scripts"

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
PODCAST_EMAIL = ""  # Fill in when available
PODCAST_LANGUAGE = "en"
PODCAST_CATEGORY = "Technology"
PODCAST_SUBCATEGORY = "Cryptocurrency"
PODCAST_EXPLICIT = "no"
BASE_URL = "https://warmidris.github.io/the-signal"
# OP3 open podcast analytics prefix — proxies downloads and logs stats
OP3_PREFIX = "https://op3.dev/e"


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

    # Format duration as HH:MM:SS
    hours = duration_secs // 3600
    minutes = (duration_secs % 3600) // 60
    seconds = duration_secs % 60
    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Generate a GUID from the filename
    guid = hashlib.sha256(filename.encode()).hexdigest()[:16]

    # Read script for description if available
    script_path = os.path.join(SCRIPTS_DIR, f"{date_str}-script.txt")
    description = ""
    if os.path.exists(script_path):
        with open(script_path) as f:
            # Use first 500 chars as description
            text = f.read()
            description = text[:500].rsplit(" ", 1)[0] + "..."

    # Parse date for pubDate
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=12, tzinfo=timezone.utc
    )
    pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

    return {
        "title": f"The Signal — {date_str}",
        "date_str": date_str,
        "pub_date": pub_date,
        "duration": duration_str,
        "duration_secs": duration_secs,
        "file_size": file_size,
        "guid": guid,
        "description": description,
        "filename": filename,
    }


def generate_feed():
    """Generate the podcast RSS XML feed."""
    # Find all episode MP3s
    episodes = sorted(glob.glob(os.path.join(EPISODES_DIR, "*.mp3")))
    if not episodes:
        print("No episodes found.")
        return

    # Build RSS
    rss = Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = SubElement(rss, "channel")

    # Channel metadata
    SubElement(channel, "title").text = PODCAST_TITLE
    SubElement(channel, "description").text = PODCAST_DESCRIPTION
    SubElement(channel, "language").text = PODCAST_LANGUAGE
    SubElement(channel, "link").text = BASE_URL

    # iTunes metadata
    SubElement(channel, "itunes:author").text = PODCAST_AUTHOR
    SubElement(channel, "itunes:summary").text = PODCAST_DESCRIPTION
    SubElement(channel, "itunes:explicit").text = PODCAST_EXPLICIT

    owner = SubElement(channel, "itunes:owner")
    SubElement(owner, "itunes:name").text = PODCAST_AUTHOR

    category = SubElement(channel, "itunes:category")
    category.set("text", PODCAST_CATEGORY)

    # Podcast cover image
    itunes_image = SubElement(channel, "itunes:image")
    itunes_image.set("href", f"{BASE_URL}/artwork/cover-3000.png")
    image = SubElement(channel, "image")
    SubElement(image, "url").text = f"{BASE_URL}/artwork/cover-3000.png"
    SubElement(image, "title").text = PODCAST_TITLE
    SubElement(image, "link").text = BASE_URL

    # Atom self-link
    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", f"{BASE_URL}/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # Episodes (newest first)
    for mp3_path in reversed(episodes):
        info = get_episode_info(mp3_path)

        item = SubElement(channel, "item")
        SubElement(item, "title").text = info["title"]
        SubElement(item, "description").text = info["description"]
        SubElement(item, "pubDate").text = info["pub_date"]
        SubElement(item, "guid").text = info["guid"]

        enclosure = SubElement(item, "enclosure")
        enclosure.set("url", f"{OP3_PREFIX}/{BASE_URL}/episodes/{info['filename']}")
        enclosure.set("length", str(info["file_size"]))
        enclosure.set("type", "audio/mpeg")

        SubElement(item, "itunes:duration").text = info["duration"]
        SubElement(item, "itunes:author").text = PODCAST_AUTHOR
        SubElement(item, "itunes:summary").text = info["description"]
        SubElement(item, "itunes:explicit").text = PODCAST_EXPLICIT

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
        print(f"  {info['title']} ({info['duration']}, {info['file_size']//1024}KB)")


if __name__ == "__main__":
    generate_feed()
