#!/usr/bin/env python3
"""Schedule rendered vertical shorts to TikTok + YouTube Shorts + Instagram Reels via Zernio.

Inputs:
  - data/podcast/clips/<episode>/*.mp4   (rendered by render_clip.py)
  - data/podcast/clips_plan/_all.json    (for caption text / hooks / topics)

Posting cadence:
  3/day at 09:00, 13:00, 19:00 ET, starting --start-date.

Usage:
  python3 scripts/podcast/schedule_shorts.py --episode "Episode April 14th 2026" \
      --start-date 2026-04-20 --dry-run
  python3 scripts/podcast/schedule_shorts.py --episode "Episode April 14th 2026" \
      --start-date 2026-04-20 --execute
"""

import argparse
import json
import mimetypes
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zernio_client import ZernioClient, ZernioError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CLIPS_DIR = ROOT / "data" / "podcast" / "clips"
CLIPS_PLAN_ALL = ROOT / "data" / "podcast" / "clips_plan" / "_all.json"

ET = ZoneInfo("America/New_York")
SLOT_HOURS = [9, 13, 19]
TARGET_PLATFORMS = ["tiktok", "youtube", "instagram"]

# Hashtags-only caption strategy per user direction. No hook line, no URL —
# profile bio carries those. Rationale: nobody reads short-form descriptions,
# so every character goes to discovery hashtags instead.
#
# Baseline 12 tags leaves headroom for ≤3 topic-specific tags → 15 max.
# YouTube Shorts IGNORES all hashtags on any post with >15 of them, so the
# cap in _caption_for() is a real ceiling, not a vibe.
DEFAULT_HASHTAGS = [
    "#fyp", "#foryoupage", "#explorepage",
    "#retrogaming", "#retrogames", "#videogames", "#gaming",
    "#nintendo", "#playstation",
    "#8bitlegacy", "#podcast", "#shorts",
]


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip().replace(" ", "_")


def _caption_for(spec: dict) -> str:
    topic_tags = [
        f"#{t.replace(' ', '').replace('-', '').lower()}"
        for t in spec.get("topics", [])[:3]
    ]
    all_tags = DEFAULT_HASHTAGS + topic_tags
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in all_tags:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(tag)
    return " ".join(deduped[:15])


def _upload_file(client: ZernioClient, path: Path) -> str:
    content_type = mimetypes.guess_type(str(path))[0] or "video/mp4"
    presigned = client.get_presigned_media_url(path.name, content_type)
    upload_url = presigned.get("uploadUrl") or presigned.get("url")
    media_url = presigned.get("mediaUrl") or presigned.get("publicUrl") or presigned.get("fileUrl")
    if not upload_url or not media_url:
        raise ZernioError(f"presigned response missing uploadUrl/mediaUrl: {presigned}")
    with path.open("rb") as f:
        r = requests.put(upload_url, data=f, headers={"Content-Type": content_type}, timeout=600)
    if r.status_code >= 300:
        raise ZernioError(f"S3 PUT failed {r.status_code}: {r.text[:300]}")
    return media_url


def _build_schedule(n_clips: int, start_date: str) -> list[datetime]:
    start = datetime.fromisoformat(start_date).replace(tzinfo=ET)
    times: list[datetime] = []
    day = 0
    slot = 0
    for _ in range(n_clips):
        dt = start.replace(hour=SLOT_HOURS[slot], minute=0, second=0, microsecond=0) + timedelta(days=day)
        times.append(dt)
        slot += 1
        if slot >= len(SLOT_HOURS):
            slot = 0
            day += 1
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


def schedule(episode: str, start_date: str, dry_run: bool = True,
             clips_plan_path: Path = CLIPS_PLAN_ALL) -> int:
    episode_clips_dir = CLIPS_DIR / _safe(episode)
    if not episode_clips_dir.exists():
        print(f"[FATAL] no clips dir: {episode_clips_dir}", file=sys.stderr)
        return 2

    mp4s = sorted(episode_clips_dir.glob("*.mp4"))
    if not mp4s:
        print(f"[FATAL] no .mp4 files in {episode_clips_dir}", file=sys.stderr)
        return 2

    plan = json.loads(clips_plan_path.read_text()) if clips_plan_path.exists() else []
    plan_by_id = {p["clip_id"]: p for p in plan}

    times = _build_schedule(len(mp4s), start_date)
    print(f"[PLAN] {len(mp4s)} clips · {SLOT_HOURS} ET · starting {start_date}")
    for mp4, when in zip(mp4s, times):
        spec = plan_by_id.get(mp4.stem, {"hook": mp4.stem, "topics": []})
        print(f"  {when.strftime('%Y-%m-%d %H:%M %Z')}  {mp4.name}  — {spec.get('title') or spec.get('hook', '')[:60]}")

    if dry_run:
        print("\n[DRY-RUN] not uploading. Re-run with --execute to push.")
        return 0

    client = ZernioClient()
    accounts = _accounts_by_platform(client)
    missing = [p for p in TARGET_PLATFORMS if p not in accounts]
    if missing:
        print(f"[FATAL] missing Zernio accounts for: {missing}. Connect them at zernio.com/dashboard.",
              file=sys.stderr)
        return 2

    log = []
    for mp4, when in zip(mp4s, times):
        spec = plan_by_id.get(mp4.stem, {"hook": mp4.stem, "topics": []})
        caption = _caption_for(spec)
        try:
            media_url = _upload_file(client, mp4)
            payload = {
                "publishAt": when.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
                "platforms": [{"platform": p, "accountId": accounts[p]} for p in TARGET_PLATFORMS],
                "media": [{"url": media_url, "type": "video"}],
                "caption": caption,
            }
            resp = client.create_post(payload)
            post_id = (resp or {}).get("id") or (resp or {}).get("data", {}).get("id")
            print(f"[OK] {mp4.name} → {post_id} @ {when.isoformat()}")
            log.append({"clip": mp4.name, "post_id": post_id, "publish_at": when.isoformat(),
                        "platforms": TARGET_PLATFORMS})
        except Exception as exc:
            print(f"[ERROR] {mp4.name}: {exc}", file=sys.stderr)
            log.append({"clip": mp4.name, "error": str(exc)})

    log_path = episode_clips_dir / "schedule_log.json"
    log_path.write_text(json.dumps(log, indent=2))
    print(f"\n[LOG] {log_path.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", default="Episode April 14th 2026")
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD (ET)")
    parser.add_argument("--clips-plan", default=str(CLIPS_PLAN_ALL))
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    return schedule(args.episode, args.start_date, dry_run=args.dry_run,
                    clips_plan_path=Path(args.clips_plan))


if __name__ == "__main__":
    sys.exit(main())
