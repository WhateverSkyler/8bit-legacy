#!/usr/bin/env python3
"""Inspect the live Zernio queue to debug duplicates / missing posts.

Lists all scheduled + recently-published posts, groups by media URL stem,
and flags clips that appear multiple times.
"""
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv  # noqa: E402

CONFIG = Path(__file__).resolve().parent.parent / "config" / ".env"
load_dotenv(CONFIG)

from zernio_client import ZernioClient  # noqa: E402

ET = ZoneInfo("America/New_York")


def stem_from_url(u: str) -> str:
    name = u.rsplit("/", 1)[-1].split("?", 1)[0]
    return name.rsplit(".", 1)[0]


def fmt_dt(s):
    if not s:
        return "—"
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(ET)
        return dt.strftime("%Y-%m-%d %H:%M ET")
    except Exception:
        return s


def main():
    c = ZernioClient()

    # All posts (no status filter — get them all)
    raw = c.list_posts(limit=200)
    posts = raw if isinstance(raw, list) else (raw.get("data") or raw.get("posts") or [])
    print(f"[ZERNIO] {len(posts)} total posts returned\n")

    by_stem = defaultdict(list)
    for p in posts:
        media = p.get("mediaItems") or p.get("media") or []
        urls = [m.get("url") or m.get("mediaUrl") or "" for m in media]
        stems = sorted({stem_from_url(u) for u in urls if u})
        key = "+".join(stems) if stems else "(no-media)"
        by_stem[key].append(p)

    # Sort by # of posts per stem desc, then by stem
    print(f"{'Stem':<40} {'#':>3}  {'Statuses':<28} {'Earliest':<22} {'Latest':<22}")
    print("-" * 120)
    for stem, lst in sorted(by_stem.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        statuses = [(p.get("status") or "?").lower() for p in lst]
        sched_times = sorted(p.get("scheduledFor") or "" for p in lst)
        earliest = fmt_dt(sched_times[0]) if sched_times else "—"
        latest = fmt_dt(sched_times[-1]) if sched_times else "—"
        flag = "  <-- DUP" if len(lst) > 1 else ""
        print(f"{stem[:38]:<40} {len(lst):>3}  {','.join(statuses)[:28]:<28} {earliest:<22} {latest:<22}{flag}")

    # Detail block for any stem with >1 posts (likely duplicates)
    dups = {k: v for k, v in by_stem.items() if len(v) > 1}
    if dups:
        print(f"\n=== DUPLICATES ({len(dups)} stems) ===")
        for stem, lst in dups.items():
            print(f"\n• {stem} ({len(lst)} posts)")
            for p in sorted(lst, key=lambda x: x.get("scheduledFor") or ""):
                pid = p.get("_id") or p.get("id")
                status = p.get("status") or "?"
                sched = fmt_dt(p.get("scheduledFor"))
                pub = fmt_dt(p.get("publishedAt") or p.get("publishedDate"))
                plats = [pl.get("platform") for pl in (p.get("platforms") or [])]
                print(f"    {pid}  status={status:<10}  scheduled={sched}  published={pub}  platforms={plats}")


if __name__ == "__main__":
    main()
