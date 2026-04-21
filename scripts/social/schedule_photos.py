#!/usr/bin/env python3
"""Schedule product photos to Instagram + Facebook via Zernio.

Inputs:
  data/social-media/final/*.png — product photos (one post per file)

For each photo:
  - Picks a caption from a short rotation of generic "store is alive" templates
  - Uploads to Zernio presigned URL → S3
  - Schedules one multi-platform post to IG + FB

Cadence:
  3 posts/week — Tue/Thu/Sat at 12:00 ET, starting on or after --start-date.

Why generic captions:
  Per user direction, these posts exist to make the socials look alive when
  someone clicks through from the web — nothing more. Not product advertising,
  not upselling. Per-photo Claude-generated captions were removed: overkill for
  the actual purpose, cost money on every run, and identical-text spam
  throttling from Meta is mitigated by the 5-entry rotation below.

Usage:
  python3 scripts/social/schedule_photos.py --start-date 2026-04-20 --preview
  python3 scripts/social/schedule_photos.py --start-date 2026-04-20 --execute
"""

import argparse
import json
import mimetypes
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zernio_client import ZernioClient, ZernioError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
# PHOTOS_DIR honors the env var so the pipeline container can point it at
# /media/photos/processing/<drop-id>/ without code changes.
PHOTOS_DIR = Path(os.getenv("PHOTOS_DIR", str(ROOT / "data" / "social-media" / "final")))
LOG_PATH = Path(os.getenv("PHOTO_LOG_PATH", str(ROOT / "data" / "social-media" / "schedule_log.json")))

ET = ZoneInfo("America/New_York")
# Tue=1, Thu=3, Sat=5 (Monday=0 per datetime.weekday()).
POST_WEEKDAYS = (1, 3, 5)
POST_HOUR_ET = 12
TARGET_PLATFORMS = ["instagram", "facebook"]

# Rotated to avoid Meta's duplicate-text spam heuristics, which throttle reach
# when every post carries identical copy.
CAPTION_ROTATION = [
    "New inventory and trade-ins at 8-Bit Legacy! Stop by or shop online at 8bitlegacy.com for the best deals on retro games and trading cards.",
    "Fresh drops at 8-Bit Legacy — retro games, Pokemon cards, and more. In-store and at 8bitlegacy.com.",
    "Stop by 8-Bit Legacy or check us out at 8bitlegacy.com. New inventory and trade-ins every week.",
    "Something new just hit the shelves at 8-Bit Legacy. Full selection at 8bitlegacy.com — retro games, trading cards, and the rare stuff you're after.",
    "What's new at 8-Bit Legacy this week? Come see us in person or shop at 8bitlegacy.com — best prices on retro games and trading cards in town.",
]

# Small brand/discovery tag set. Photo posts aren't chasing virality.
CAPTION_HASHTAGS = "#8bitlegacy #retrogaming #pokemoncards #videogames #valdostaga"


def _caption_for(index: int) -> str:
    base = CAPTION_ROTATION[index % len(CAPTION_ROTATION)]
    return f"{base}\n\n{CAPTION_HASHTAGS}"


def _upload_file(client: ZernioClient, path: Path) -> str:
    content_type = mimetypes.guess_type(str(path))[0] or "image/png"
    presigned = client.get_presigned_media_url(path.name, content_type)
    upload_url = presigned.get("uploadUrl") or presigned.get("url")
    media_url = presigned.get("mediaUrl") or presigned.get("publicUrl") or presigned.get("fileUrl")
    if not upload_url or not media_url:
        raise ZernioError(f"presigned response missing uploadUrl/mediaUrl: {presigned}")
    with path.open("rb") as f:
        r = requests.put(upload_url, data=f, headers={"Content-Type": content_type}, timeout=300)
    if r.status_code >= 300:
        raise ZernioError(f"S3 PUT failed {r.status_code}: {r.text[:300]}")
    return media_url


def _build_schedule(n: int, start_date: str) -> list[datetime]:
    """Return n datetimes — one per post — each on a Tue/Thu/Sat at POST_HOUR_ET.

    Starts at --start-date midnight ET, rolls forward to the first Tue/Thu/Sat at
    POST_HOUR_ET, then advances one qualifying day per item.
    """
    start = datetime.fromisoformat(start_date).replace(tzinfo=ET)
    cursor = start.replace(hour=POST_HOUR_ET, minute=0, second=0, microsecond=0)
    # If start_date is past POST_HOUR_ET on the day itself, skip to tomorrow.
    if cursor < start:
        cursor = cursor + timedelta(days=1)
    times: list[datetime] = []
    for _ in range(n):
        while cursor.weekday() not in POST_WEEKDAYS:
            cursor = cursor + timedelta(days=1)
        times.append(cursor)
        cursor = cursor + timedelta(days=1)
    return times


def _accounts_by_platform(client: ZernioClient) -> dict[str, str]:
    raw = client.list_accounts()
    if isinstance(raw, dict):
        items = raw.get("accounts") or raw.get("data") or []
    else:
        items = raw or []
    out: dict[str, str] = {}
    for acct in items:
        platform = (acct.get("platform") or "").lower()
        acct_id = acct.get("_id") or acct.get("id") or acct.get("accountId")
        if platform and acct_id and platform not in out:
            out[platform] = acct_id
    return out


def run(start_date: str, execute: bool) -> int:
    photos = sorted(PHOTOS_DIR.glob("*.png"))
    photos = [p for p in photos if not p.name.startswith("._") and "template" not in p.name.lower()]
    if not photos:
        print(f"[FATAL] no PNGs in {PHOTOS_DIR}", file=sys.stderr)
        return 2

    times = _build_schedule(len(photos), start_date)
    print(f"[PLAN] {len(photos)} photos · IG+FB · Tue/Thu/Sat {POST_HOUR_ET}:00 ET from {start_date}\n")

    rows = []
    for i, (photo, when) in enumerate(zip(photos, times)):
        caption = _caption_for(i)
        rows.append((photo, when, caption))
        print(f"  {when.strftime('%Y-%m-%d %H:%M %Z')}  {photo.name:<42} — {caption[:60]}…")

    if not execute:
        print("\n[PREVIEW] not uploading. Re-run with --execute to push.")
        return 0

    client = ZernioClient()
    accounts = _accounts_by_platform(client)
    missing = [p for p in TARGET_PLATFORMS if p not in accounts]
    if missing:
        print(f"[FATAL] missing Zernio accounts: {missing}. Connect at zernio.com/dashboard.",
              file=sys.stderr)
        return 2

    log = []
    ok_count = 0
    err_count = 0
    for photo, when, caption in rows:
        try:
            media_url = _upload_file(client, photo)
            payload = {
                "scheduledFor": when.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
                "timezone": "America/New_York",
                "platforms": [{"platform": p, "accountId": accounts[p]} for p in TARGET_PLATFORMS],
                "mediaItems": [{"url": media_url, "type": "image"}],
                "content": caption,
            }
            resp = client.create_post(payload)
            post_id = (
                (resp or {}).get("_id")
                or (resp or {}).get("id")
                or (resp or {}).get("data", {}).get("_id")
                or (resp or {}).get("data", {}).get("id")
            )
            print(f"[OK] {photo.name} → {post_id} @ {when.isoformat()}")
            log.append({"photo": photo.name, "post_id": post_id, "publish_at": when.isoformat()})
            ok_count += 1
        except Exception as exc:
            print(f"[ERROR] {photo.name}: {exc}", file=sys.stderr)
            log.append({"photo": photo.name, "error": str(exc)})
            err_count += 1

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2))
    try:
        log_display = str(LOG_PATH.relative_to(ROOT))
    except ValueError:
        log_display = str(LOG_PATH)
    print(f"\n[LOG] {log_display} — {ok_count} scheduled, {err_count} failed")
    if ok_count == 0 and err_count > 0:
        print("[FATAL] all posts failed — drop will NOT be marked processed", file=sys.stderr)
        return 3
    if err_count > 0:
        print(f"[WARN] {err_count} posts failed (partial success)", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD (ET)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--preview", action="store_true")
    g.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    return run(args.start_date, execute=args.execute)


if __name__ == "__main__":
    sys.exit(main())
