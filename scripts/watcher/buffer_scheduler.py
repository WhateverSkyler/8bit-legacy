#!/usr/bin/env python3
"""Buffer scheduler — re-posts clips from the archive when the Zernio queue runs low.

Per user direction 2026-04-20:
- Minimum 1 short/day, buffer fills gaps between biweekly episodes
- Repeating clips across posts is explicitly fine (algorithm re-rolls)
- More posts > fewer posts as long as content quality holds

Invoked by drop_watcher every BUFFER_EVERY_N_POLLS cycles (default ~60 min).
Also safe to run manually for one-off reconciliation.

State at /media/state/buffer_scheduler.json tracks last-reposted-at per clip path
(cooldown enforcement) plus last-run timestamp.

Logic (single pass):
  1. Query Zernio for posts scheduled in the next BUFFER_HORIZON_DAYS
  2. Count shorts per day (tiktok/youtube/instagram + media.type=video)
  3. Identify day/slot gaps below BUFFER_POSTS_PER_DAY target
  4. Pick eligible archive clips (outside cooldown), prioritize least-recently-reposted
  5. Upload + schedule into the gaps at the standard 9/13/19 ET slots
  6. Update state

Failure → Navi task. Success → logs only.
"""

from __future__ import annotations

import json
import mimetypes
import os
import random
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

_SCRIPTS_ROOT = Path(os.getenv("SCRIPTS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(_SCRIPTS_ROOT))
from navi_alerts import emit_navi_task  # noqa: E402
from zernio_client import ZernioClient, ZernioError  # noqa: E402

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/media"))
CLIPS_ARCHIVE = MEDIA_ROOT / "podcast" / "clips-archive"
STATE_FILE = MEDIA_ROOT / "state" / "buffer_scheduler.json"
ET = ZoneInfo("America/New_York")

# Targets and constraints
BUFFER_HORIZON_DAYS = int(os.getenv("BUFFER_HORIZON_DAYS", "7"))
BUFFER_POSTS_PER_DAY = int(os.getenv("BUFFER_POSTS_PER_DAY", "3"))  # fill up to 3 (9/13/19 ET)
BUFFER_COOLDOWN_DAYS = int(os.getenv("BUFFER_COOLDOWN_DAYS", "21"))
BUFFER_MAX_SCHEDULE_PER_RUN = int(os.getenv("BUFFER_MAX_SCHEDULE_PER_RUN", "15"))

SLOT_HOURS = [9, 13, 19]
TARGET_PLATFORMS = ["tiktok", "youtube", "instagram"]

# Hashtag set mirrors schedule_shorts.py — if that file changes, mirror here.
DEFAULT_HASHTAGS = [
    "#fyp", "#foryoupage", "#explorepage",
    "#retrogaming", "#retrogames", "#videogames", "#gaming",
    "#nintendo", "#playstation",
    "#8bitlegacy", "#podcast", "#shorts",
]


def _log(msg: str) -> None:
    print(f"[BUFFER] {msg}", flush=True)


# --- State -----------------------------------------------------------------

def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_posted": {}, "last_run": None, "total_reposts": 0, "alert_throttle": {}}
    try:
        state = json.loads(STATE_FILE.read_text())
        state.setdefault("alert_throttle", {})
        return state
    except (OSError, json.JSONDecodeError):
        return {"last_posted": {}, "last_run": None, "total_reposts": 0, "alert_throttle": {}}


# 2026-04-29: switched from 24h time-based throttle to state-based "active alert"
# tracking. Old behavior re-fired the same Navi task daily for chronic conditions
# like "no eligible archive clips" — Tristan saw it every morning. New behavior:
# fire once when the condition becomes true, stay quiet, and only re-fire after
# the condition has resolved AND recurred. The alert_throttle dict now stores
# `True` (or a timestamp for back-compat) for active alerts; missing/falsy = clear.


def _should_emit_alert(state: dict, key: str, now: datetime | None = None) -> bool:
    """Emit only if this alert isn't already in active state."""
    return not state.get("alert_throttle", {}).get(key)


def _mark_alert(state: dict, key: str, now: datetime | None = None) -> None:
    """Record that this alert is currently active (Navi task already posted)."""
    state.setdefault("alert_throttle", {})[key] = now.isoformat() if now else True


def _clear_alert(state: dict, key: str) -> None:
    """Mark this alert as resolved so the next occurrence re-fires."""
    state.setdefault("alert_throttle", {}).pop(key, None)


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# --- Archive loading -------------------------------------------------------

def _load_clip_metadata() -> dict[str, dict]:
    """Walk clips-archive for `_all.json` sidecars — maps clip_id → {title, hook, topics, ...}."""
    metadata: dict[str, dict] = {}
    for plan_path in CLIPS_ARCHIVE.rglob("_all.json"):
        try:
            picks = json.loads(plan_path.read_text())
            for p in picks:
                if "clip_id" in p:
                    metadata[p["clip_id"]] = p
        except (OSError, json.JSONDecodeError):
            continue
    return metadata


def _caption_for(meta: dict) -> str:
    """Mirror schedule_shorts.py's caption logic: hashtags only, capped at 15."""
    topic_tags = [
        f"#{t.replace(' ', '').replace('-', '').lower()}"
        for t in meta.get("topics", [])[:3]
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


# --- Zernio helpers --------------------------------------------------------

def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(ET)
    except (ValueError, AttributeError):
        return None


def _count_scheduled_per_day(client: ZernioClient, now: datetime, horizon: datetime) -> dict[date, int]:
    """Query Zernio posts and bucket qualifying shorts by ET calendar day.

    2026-04-29: paginate. Zernio's /posts response is `{posts:[…], pagination:{…}}`
    with a default page size of 10. Without pagination the buffer was only seeing
    the first 10 posts (often promotional photos that don't count as shorts) and
    spuriously concluding the queue had gaps.
    """
    posts: list = []
    page = 1
    PAGE_LIMIT = 50
    MAX_PAGES = 50  # safety rail
    while page <= MAX_PAGES:
        try:
            raw = client._request("GET", "/posts", params={"page": page, "limit": PAGE_LIMIT})
        except ZernioError:
            break
        if isinstance(raw, list):
            posts.extend(raw)
            break
        page_posts = raw.get("posts") or raw.get("data") or []
        if not page_posts:
            break
        posts.extend(page_posts)
        if len(page_posts) < PAGE_LIMIT:
            break
        page += 1

    per_day: dict[date, int] = {}
    for p in posts:
        dt = _parse_dt(
            p.get("scheduledFor")
            or p.get("publishAt")
            or p.get("publish_at")
            or p.get("scheduledAt")
        )
        if not dt or dt < now or dt > horizon:
            continue
        media = p.get("mediaItems") or p.get("media") or []
        if not any(((m.get("type") or "").lower() == "video") for m in media):
            continue
        platforms = [(pl.get("platform") or "").lower() for pl in (p.get("platforms") or [])]
        if not any(pl in TARGET_PLATFORMS for pl in platforms):
            continue
        per_day[dt.date()] = per_day.get(dt.date(), 0) + 1
    return per_day


def _find_gaps(now: datetime, per_day: dict[date, int]) -> list[datetime]:
    """Return list of datetimes where shorts should be scheduled to hit the target."""
    gaps: list[datetime] = []
    for i in range(BUFFER_HORIZON_DAYS):
        d = (now + timedelta(days=i)).date()
        have = per_day.get(d, 0)
        need = max(0, BUFFER_POSTS_PER_DAY - have)
        # Fill from the later slots first so any manually-scheduled content keeps the best slots
        for offset in range(need):
            slot_idx = BUFFER_POSTS_PER_DAY - 1 - offset  # e.g. 19 → 13 → 9
            hour = SLOT_HOURS[min(slot_idx, len(SLOT_HOURS) - 1)]
            slot = datetime.combine(d, datetime.min.time()).replace(tzinfo=ET, hour=hour)
            if slot > now + timedelta(minutes=10):
                gaps.append(slot)
    gaps.sort()
    return gaps


def _accounts_by_platform(client: ZernioClient) -> dict[str, str]:
    raw = client.list_accounts()
    items = raw if isinstance(raw, list) else (raw.get("accounts") or raw.get("data") or [])
    out: dict[str, str] = {}
    for a in items:
        p = (a.get("platform") or "").lower()
        aid = a.get("_id") or a.get("id") or a.get("accountId")
        if p and aid and p not in out:
            out[p] = aid
    return out


def _upload_file(client: ZernioClient, path: Path) -> str:
    content_type = mimetypes.guess_type(str(path))[0] or "video/mp4"
    presigned = client.get_presigned_media_url(path.name, content_type)
    upload_url = presigned.get("uploadUrl") or presigned.get("url")
    media_url = presigned.get("mediaUrl") or presigned.get("publicUrl") or presigned.get("fileUrl")
    if not upload_url or not media_url:
        raise ZernioError(f"presigned response missing url fields: {presigned}")
    with path.open("rb") as f:
        r = requests.put(upload_url, data=f, headers={"Content-Type": content_type}, timeout=600)
    if r.status_code >= 300:
        raise ZernioError(f"S3 PUT failed {r.status_code}: {r.text[:200]}")
    return media_url


# --- Main ------------------------------------------------------------------

def _eligible_archive_clips(state: dict, now: datetime,
                             metadata: dict[str, dict] | None = None) -> tuple[list[Path], list[Path]]:
    """Return (eligible_clips, never_posted_clips).

    `eligible_clips` are repost-safe: outside cooldown AND marked evergreen
    (or unmarked, with REQUIRE_EVERGREEN=False env override). Never-posted
    clips are returned separately so the caller can distinguish "fresh
    content available" from "only reposts available" — that distinction
    drives the pre-emptive "running low" alert added 2026-04-29.

    Per Tristan 2026-04-29: time-sensitive clips ("Nintendo just announced")
    must NOT be reposted, since they look stale months later. Evergreen
    clips (Zelda rankings, game-discussion takes) ARE safe to repost.
    `evergreen` field is set by pick_clips.py's Claude prompt; legacy
    clips without the field default to NOT-evergreen (safe-by-default).
    """
    clips = list(CLIPS_ARCHIVE.rglob("*.mp4"))
    if not clips:
        return [], []
    last_posted = state.get("last_posted", {})
    metadata = metadata or {}
    require_evergreen = os.getenv("BUFFER_REQUIRE_EVERGREEN", "1") not in ("0", "false", "False", "")

    eligible: list[tuple[Path, datetime]] = []
    never_posted: list[Path] = []
    for clip in clips:
        key = str(clip)
        last_str = last_posted.get(key)
        # Look up clip's evergreen status from metadata (clip_id = filename stem)
        meta = metadata.get(clip.stem, {})
        is_evergreen = bool(meta.get("evergreen", False))

        if last_str:
            last_dt = _parse_dt(last_str)
            if last_dt and (now - last_dt).days < BUFFER_COOLDOWN_DAYS:
                continue
            sort_key = last_dt or datetime(1970, 1, 1, tzinfo=ET)
            # Repost-eligibility requires evergreen (unless override)
            if require_evergreen and not is_evergreen:
                continue
        else:
            sort_key = datetime(1970, 1, 1, tzinfo=ET)
            never_posted.append(clip)
        eligible.append((clip, sort_key))

    # Never-reposted first, then oldest-reposted — spreads the love
    eligible.sort(key=lambda t: t[1])
    return [c for c, _ in eligible], never_posted


def run() -> int:
    if not CLIPS_ARCHIVE.exists():
        _log(f"clips-archive not at {CLIPS_ARCHIVE} — nothing to do yet")
        return 0

    state = _load_state()
    now = datetime.now(ET)
    horizon = now + timedelta(days=BUFFER_HORIZON_DAYS)

    try:
        client = ZernioClient()
    except ZernioError as exc:
        emit_navi_task(
            title="Buffer scheduler: Zernio not configured",
            description=f"{exc}. Set ZERNIO_API_KEY in the pipeline container's .env.",
            priority="high",
        )
        return 2

    per_day = _count_scheduled_per_day(client, now, horizon)
    total_scheduled = sum(per_day.values())
    _log(f"scheduled in next {BUFFER_HORIZON_DAYS}d: {total_scheduled} shorts across {len(per_day)} days")

    gaps = _find_gaps(now, per_day)
    if not gaps:
        _log("no gaps to fill")
        state["last_run"] = now.isoformat()
        _save_state(state)
        return 0

    gaps = gaps[:BUFFER_MAX_SCHEDULE_PER_RUN]
    _log(f"will fill {len(gaps)} gap slots")

    metadata = _load_clip_metadata()
    eligible, never_posted = _eligible_archive_clips(state, now, metadata)

    # Pre-emptive "running low" alert: fires once when never-posted clips run
    # out BUT we still have evergreen reposts available to fill gaps. This
    # gives Tristan warning to record a new episode BEFORE repeats start.
    # Per his ask 2026-04-29: alert me that we need new content before reusing
    # old. Distinct from "no_eligible_clips" (archive is empty / cooldown-blocked
    # / no evergreen clips at all) — that's a harder-fail state handled below.
    if gaps and not never_posted and eligible:
        if _should_emit_alert(state, "running_low_on_fresh"):
            emit_navi_task(
                title="Buffer scheduler: out of fresh shorts — record next episode",
                description=(
                    f"The {len(gaps)} upcoming gap slots in the next "
                    f"{BUFFER_HORIZON_DAYS}d will be filled by REPOSTS of evergreen "
                    f"archive clips. No never-posted clips remain. To keep posting "
                    f"fresh content, drop a new podcast episode in the NAS incoming/ "
                    f"folder. Reposts proceed automatically until then."
                ),
                priority="medium",
            )
            _mark_alert(state, "running_low_on_fresh", now)
    elif never_posted:
        # Fresh content available again → clear the warning
        _clear_alert(state, "running_low_on_fresh")

    if not eligible:
        if _should_emit_alert(state, "no_eligible_clips"):
            emit_navi_task(
                title="Buffer scheduler: no eligible archive clips",
                description=(
                    f"All archive clips are within the {BUFFER_COOLDOWN_DAYS}-day cooldown "
                    f"or the archive is empty. Drop a new podcast episode or reduce "
                    f"BUFFER_COOLDOWN_DAYS env var."
                ),
                priority="medium",
            )
            _mark_alert(state, "no_eligible_clips", now)
        else:
            _log("no eligible clips (alert already active — suppressed until condition resolves)")
        state["last_run"] = now.isoformat()
        _save_state(state)
        return 0

    # We have eligible clips again — clear the alert so a future depletion re-fires.
    _clear_alert(state, "no_eligible_clips")

    accounts = _accounts_by_platform(client)
    missing = [p for p in TARGET_PLATFORMS if p not in accounts]
    if missing:
        if _should_emit_alert(state, "zernio_account_missing"):
            emit_navi_task(
                title="Buffer scheduler: Zernio account not connected",
                description=f"Missing: {missing}. Reconnect in the Zernio dashboard.",
                priority="high",
            )
            _mark_alert(state, "zernio_account_missing", now)
        state["last_run"] = now.isoformat()
        _save_state(state)
        return 2

    # All required Zernio accounts present — clear that alert too.
    _clear_alert(state, "zernio_account_missing")

    last_posted = state.setdefault("last_posted", {})

    # Interleave to reduce same-episode clumping when picking
    random.shuffle(eligible[:50])
    filled = 0
    for gap, clip_path in zip(gaps, eligible):
        clip_id = clip_path.stem
        meta = metadata.get(clip_id, {"topics": []})
        caption = _caption_for(meta)
        try:
            media_url = _upload_file(client, clip_path)
            payload = {
                "scheduledFor": gap.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
                "timezone": "America/New_York",
                "platforms": [{"platform": p, "accountId": accounts[p]} for p in TARGET_PLATFORMS],
                "mediaItems": [{"url": media_url, "type": "video"}],
                "content": caption,
            }
            resp = client.create_post(payload)
            post_id = (resp or {}).get("id") or (resp or {}).get("data", {}).get("id")
            last_posted[str(clip_path)] = now.isoformat()
            state["total_reposts"] = state.get("total_reposts", 0) + 1
            _log(f"scheduled {clip_path.name} @ {gap.isoformat()} (post_id={post_id})")
            filled += 1
        except Exception as exc:
            _log(f"FAIL {clip_path.name}: {exc}")
            emit_navi_task(
                title=f"Buffer scheduler: failed to upload {clip_path.name}",
                description=f"{exc!r}",
                priority="medium",
            )

    state["last_run"] = now.isoformat()
    _save_state(state)
    _log(f"done: filled {filled}/{len(gaps)} gaps")
    return 0


def main() -> int:
    try:
        return run()
    except Exception as exc:
        emit_navi_task(
            title="Buffer scheduler crashed",
            description=f"Unhandled exception: {exc!r}",
            priority="high",
        )
        raise


if __name__ == "__main__":
    sys.exit(main())
