#!/usr/bin/env python3
"""Delete still-pending Zernio posts for an episode's shorts.

Used when a rendered batch needs to be re-rendered + re-scheduled (e.g., a
crop/caption bug was shipped). If schedule_shorts.py gets re-run without
deleting the existing queue first, Zernio happily schedules duplicates.

Matching strategy:
  1. Preferred — read `data/podcast/clips/<episode>/schedule_log.json` and
     delete every `post_id` that's still in `scheduled` state.
  2. Fallback — list all currently-scheduled Zernio posts and delete those
     whose `mediaItems[].url` contains any clip stem from the episode dir
     (e.g., "05-c1.mp4"). Safe for cases where the log was lost or the
     deploy rebuilt the container and wiped state.

Defaults to --dry-run (prints what it WOULD delete). Pass --execute to
actually call the Zernio DELETE endpoint.

Usage:
  python3 scripts/podcast/cleanup_zernio_queue.py --episode "Episode April 14th 2026"
  python3 scripts/podcast/cleanup_zernio_queue.py --episode "Episode April 14th 2026" --execute
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zernio_client import ZernioClient, ZernioError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CLIPS_DIR = ROOT / "data" / "podcast" / "clips"


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip().replace(" ", "_")


def _list_scheduled(client: ZernioClient) -> list[dict]:
    try:
        raw = client.list_posts(status="scheduled")
    except ZernioError:
        raw = client.list_posts()
    if isinstance(raw, list):
        posts = raw
    else:
        posts = raw.get("data") or raw.get("posts") or []
    return [p for p in posts if (p.get("status") or "").lower() in ("scheduled", "pending", "")]


def _post_id(p: dict) -> str | None:
    return p.get("_id") or p.get("id") or (p.get("data") or {}).get("_id")


def _media_urls(p: dict) -> list[str]:
    media = p.get("mediaItems") or p.get("media") or []
    out: list[str] = []
    for m in media:
        u = m.get("url") or m.get("mediaUrl") or m.get("publicUrl")
        if u:
            out.append(u)
    return out


def cleanup(episode: str, execute: bool) -> int:
    episode_dir = CLIPS_DIR / _safe(episode)
    if not episode_dir.exists():
        print(f"[FATAL] no clips dir: {episode_dir}", file=sys.stderr)
        return 2

    clip_stems = sorted({p.stem for p in episode_dir.glob("*.mp4")})
    if not clip_stems:
        print(f"[FATAL] no .mp4 files in {episode_dir} — render first?", file=sys.stderr)
        return 2
    print(f"[SCOPE] episode={episode}  clips on disk: {len(clip_stems)}")
    print(f"        {clip_stems}")

    client = ZernioClient()

    # --- Strategy 1: schedule_log.json ---
    log_path = episode_dir / "schedule_log.json"
    targets: list[tuple[str, str]] = []  # (post_id, match_reason)
    logged_ids: set[str] = set()
    if log_path.exists():
        try:
            entries = json.loads(log_path.read_text())
            for e in entries:
                pid = e.get("post_id")
                if pid:
                    logged_ids.add(pid)
                    targets.append((pid, f"schedule_log:{e.get('clip', '')}"))
            print(f"[LOG] {log_path.name}: {len(logged_ids)} post ids")
        except Exception as exc:
            print(f"[LOG] failed to parse {log_path.name}: {exc}")

    # --- Strategy 2: list scheduled + URL-match clip stems ---
    try:
        scheduled = _list_scheduled(client)
    except ZernioError as exc:
        print(f"[ERROR] list_posts failed: {exc}", file=sys.stderr)
        scheduled = []
    print(f"[ZERNIO] {len(scheduled)} currently-scheduled posts returned by API")

    for p in scheduled:
        pid = _post_id(p)
        if not pid or pid in logged_ids:
            continue
        urls = _media_urls(p)
        hit = next((s for s in clip_stems if any(s in u for u in urls)), None)
        if hit:
            targets.append((pid, f"url-match:{hit}"))

    # Dedup preserving order
    seen: set[str] = set()
    unique_targets: list[tuple[str, str]] = []
    for pid, reason in targets:
        if pid in seen:
            continue
        seen.add(pid)
        unique_targets.append((pid, reason))

    if not unique_targets:
        print("[DONE] nothing to delete")
        return 0

    print(f"\n[PLAN] would delete {len(unique_targets)} Zernio posts:")
    for pid, reason in unique_targets:
        print(f"  - {pid}  ({reason})")

    if not execute:
        print("\n[DRY-RUN] pass --execute to actually delete.")
        return 0

    ok = fail = 0
    for pid, reason in unique_targets:
        try:
            client.delete_post(pid)
            print(f"[OK]    {pid}")
            ok += 1
        except ZernioError as exc:
            # 404 = already gone (fine); other codes worth logging
            print(f"[ERROR] {pid}: {exc}", file=sys.stderr)
            fail += 1

    print(f"\n[DONE] deleted {ok}, failed {fail}")
    return 0 if fail == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True, help="Episode name, e.g. 'Episode April 14th 2026'")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True,
                   help="Print intended deletions without calling the API (default).")
    g.add_argument("--execute", action="store_true",
                   help="Actually delete the matched posts.")
    args = parser.parse_args()
    return cleanup(args.episode, execute=args.execute)


if __name__ == "__main__":
    sys.exit(main())
