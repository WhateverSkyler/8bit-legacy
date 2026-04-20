#!/usr/bin/env python3
"""Schedule product photos to Instagram + Facebook via Zernio.

Inputs:
  data/social-media/final/*.png — product photos (one post per file)

For each photo:
  - Generates a hype caption + 3-5 hashtags via Claude (8-Bit Legacy voice)
  - Uploads to Zernio presigned URL → S3
  - Schedules one multi-platform post to IG + FB

Cadence:
  2 posts/day at 10:00 ET and 18:00 ET, starting --start-date.

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
PHOTOS_DIR = ROOT / "data" / "social-media" / "final"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
except ImportError:
    pass
LOG_PATH = ROOT / "data" / "social-media" / "schedule_log.json"
CAPTIONS_CACHE = ROOT / "data" / "social-media" / "captions_cache.json"

ET = ZoneInfo("America/New_York")
SLOT_HOURS = [10, 18]
TARGET_PLATFORMS = ["instagram", "facebook"]

CAPTION_SYSTEM = """You write Instagram + Facebook captions for 8-Bit Legacy, a retro gaming &
Pokemon card store (8bitlegacy.com). Voice: casual, collector-nostalgic, slightly snarky, never
corporate. Hype without hyperbole.

Return ONLY strict JSON: {caption, hashtags}.
- caption: 1-3 sentences, ≤220 chars. Reference the actual item from the filename. End with a
  light CTA ("shop now", "link in bio", "DM to grab", etc.) or a question.
- hashtags: array of 4-6 lowercase hashtags, mix of broad (#retrogaming, #nintendo) +
  specific to the item."""


def _caption_for(filename: str) -> dict:
    import anthropic

    cache: dict = {}
    if CAPTIONS_CACHE.exists():
        try:
            cache = json.loads(CAPTIONS_CACHE.read_text())
        except json.JSONDecodeError:
            cache = {}
    if filename in cache:
        return cache[filename]

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    stem = Path(filename).stem
    prompt = f"Product photo filename: {stem}\nWrite the caption + hashtags."
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=CAPTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    data = json.loads(text)
    cache[filename] = data
    CAPTIONS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    CAPTIONS_CACHE.write_text(json.dumps(cache, indent=2))
    return data


def _compose_caption(data: dict) -> str:
    caption = data["caption"].strip()
    tags = " ".join(data.get("hashtags", []))
    return f"{caption}\n\n8bitlegacy.com\n{tags}"


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
    start = datetime.fromisoformat(start_date).replace(tzinfo=ET)
    times: list[datetime] = []
    day = 0
    slot = 0
    for _ in range(n):
        dt = start.replace(hour=SLOT_HOURS[slot], minute=0, second=0, microsecond=0) + timedelta(days=day)
        times.append(dt)
        slot += 1
        if slot >= len(SLOT_HOURS):
            slot = 0
            day += 1
    return times


def _accounts_by_platform(client: ZernioClient) -> dict[str, str]:
    accounts = client.list_accounts()
    items = accounts.get("data") if isinstance(accounts, dict) else accounts
    out: dict[str, str] = {}
    for acct in items or []:
        platform = (acct.get("platform") or "").lower()
        acct_id = acct.get("id") or acct.get("accountId")
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
    print(f"[PLAN] {len(photos)} photos · IG+FB · 2/day at {SLOT_HOURS} ET from {start_date}\n")

    rows = []
    for photo, when in zip(photos, times):
        try:
            data = _caption_for(photo.name)
            caption_preview = data["caption"][:60]
        except Exception as exc:
            print(f"[WARN] caption gen failed for {photo.name}: {exc}")
            data = {"caption": f"Check out {photo.stem}!", "hashtags": ["#retrogaming", "#8bitlegacy"]}
            caption_preview = data["caption"][:60]
        rows.append((photo, when, data))
        print(f"  {when.strftime('%Y-%m-%d %H:%M %Z')}  {photo.name:<42} — {caption_preview}")

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
    for photo, when, data in rows:
        try:
            media_url = _upload_file(client, photo)
            payload = {
                "publishAt": when.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
                "platforms": [{"platform": p, "accountId": accounts[p]} for p in TARGET_PLATFORMS],
                "media": [{"url": media_url, "type": "image"}],
                "caption": _compose_caption(data),
            }
            resp = client.create_post(payload)
            post_id = (resp or {}).get("id") or (resp or {}).get("data", {}).get("id")
            print(f"[OK] {photo.name} → {post_id} @ {when.isoformat()}")
            log.append({"photo": photo.name, "post_id": post_id, "publish_at": when.isoformat()})
        except Exception as exc:
            print(f"[ERROR] {photo.name}: {exc}", file=sys.stderr)
            log.append({"photo": photo.name, "error": str(exc)})

    LOG_PATH.write_text(json.dumps(log, indent=2))
    print(f"\n[LOG] {LOG_PATH.relative_to(ROOT)}")
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
