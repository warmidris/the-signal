#!/usr/bin/env python3
"""Fetch signals from aibtc.news API for a given date range."""

import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

API_BASE = "https://aibtc.news/api"


def fetch_signals(since=None, limit=100):
    """Fetch signals, optionally filtering by timestamp."""
    url = f"{API_BASE}/signals?limit={limit}"
    if since:
        url += f"&since={since}"
    req = urllib.request.Request(url, headers={"User-Agent": "Idris-Podcast/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_beats():
    """Fetch all beats (categories)."""
    url = f"{API_BASE}/beats"
    req = urllib.request.Request(url, headers={"User-Agent": "Idris-Podcast/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def signals_for_date(target_date_str):
    """Get all signals filed on a specific date (UTC).

    Returns signals sorted by timestamp.
    """
    target = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    day_start = target.isoformat()
    day_end = (target + timedelta(days=1)).isoformat()

    # Fetch signals since start of day
    data = fetch_signals(since=day_start, limit=100)
    signals = data.get("signals", [])

    # Filter to only signals within the target day
    day_signals = []
    for s in signals:
        ts = s.get("timestamp", "")
        if ts >= day_start and ts < day_end:
            day_signals.append(s)

    # Sort by timestamp
    day_signals.sort(key=lambda s: s["timestamp"])
    return day_signals


def main():
    if len(sys.argv) < 2:
        # Default: fetch today's signals
        target = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        target = sys.argv[1]

    signals = signals_for_date(target)

    print(f"Date: {target}")
    print(f"Signals found: {len(signals)}")
    print()

    for s in signals:
        print(f"[{s['beat']}] {s['headline']}")
        print(f"  {s['content'][:200]}...")
        print()

    # Also dump full JSON
    outfile = f"/agent/work/podcast/scripts/{target}-signals.json"
    with open(outfile, "w") as f:
        json.dump({"date": target, "signals": signals}, f, indent=2)
    print(f"Full data saved to {outfile}")


if __name__ == "__main__":
    main()
