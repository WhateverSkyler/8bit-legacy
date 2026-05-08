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
from podcast._caption import merged_hashtags, truncate_title  # noqa: E402
from podcast.pick_clips import _validate_title  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CLIPS_DIR = ROOT / "data" / "podcast" / "clips"
CLIPS_PLAN_ALL = ROOT / "data" / "podcast" / "clips_plan" / "_all.json"

ET = ZoneInfo("America/New_York")
SLOT_HOURS = [9, 13, 19]
TARGET_PLATFORMS = ["tiktok", "youtube", "instagram", "facebook"]


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip().replace(" ", "_")


def _qa_title(spec: dict) -> tuple[str, list[str]]:
    """Return (final_title_for_caption, list_of_warnings)."""
    raw = (spec.get("title") or "").strip()
    warnings: list[str] = []
    if not raw:
        return "", ["no title in spec"]
    ok, reason = _validate_title(raw)
    if not ok:
        warnings.append(f"title QA failed: {reason}")
    final, was_truncated = truncate_title(raw)
    if was_truncated:
        warnings.append(f"title truncated from {len(raw)} → {len(final)} chars")
    return final, warnings


def _caption_for(spec: dict) -> str:
    final_title, _ = _qa_title(spec)
    hashtags = merged_hashtags(spec.get("topics", []))
    if final_title:
        return f"{final_title}\n\n{hashtags}"
    return hashtags


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


def _build_schedule(n_clips: int, start_date: str, skip_past: bool = True) -> list[datetime]:
    """Build n_clips scheduling times at 9/13/19 ET starting from start_date.
    If skip_past (default), drop any slot already in the past so the first
    returned slot is always future. Useful when rescheduling mid-day.
    """
    start = datetime.fromisoformat(start_date).replace(tzinfo=ET)
    now = datetime.now(tz=ET)
    times: list[datetime] = []
    day = 0
    slot = 0
    # Produce enough candidates to satisfy n_clips even after skipping past ones.
    # Safety cap prevents infinite loops if inputs are nonsense.
    while len(times) < n_clips:
        dt = start.replace(hour=SLOT_HOURS[slot], minute=0, second=0, microsecond=0) + timedelta(days=day)
        if not (skip_past and dt <= now):
            times.append(dt)
        slot += 1
        if slot >= len(SLOT_HOURS):
            slot = 0
            day += 1
        if day > 30:  # safety: don't scan beyond a month
            break
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


def _previously_posted_stems() -> set[str]:
    """Return the set of clip stems that appear in any past schedule_log.json
    across all episodes. Used to skip clips that have already been pushed to
    Zernio in any prior run, preventing the duplicate-posting failure mode
    where re-running schedule_shorts.py on a folder containing carry-over
    clips re-schedules them. (2026-05-07 user-flagged duplicate posts.)"""
    posted: set[str] = set()
    for log in CLIPS_DIR.glob("*/schedule_log.json"):
        try:
            entries = json.loads(log.read_text())
        except Exception:
            continue
        for e in entries:
            stem = (e.get("clip") or "").rsplit("/", 1)[-1]
            if stem:
                posted.add(stem)
    return posted


def _scheduled_in_zernio_stems(client: ZernioClient | None) -> set[str]:
    """Return the set of clip stems currently scheduled in Zernio (any
    platform, any account). Best-effort: if Zernio is unreachable, returns
    empty set rather than blocking the run."""
    if client is None:
        return set()
    try:
        resp = client.list_posts(status="scheduled", limit=500)
    except Exception:
        return set()
    items = resp.get("posts") if isinstance(resp, dict) else resp
    if not isinstance(items, list):
        return set()
    stems: set[str] = set()
    for p in items:
        for m in p.get("mediaItems", []) or []:
            url = m.get("url") or ""
            raw = url.rsplit("/", 1)[-1].split("?")[0]
            # Zernio prepends "<ts>_<rand>_" to uploaded filenames; strip it.
            parts = raw.split("_", 2)
            stem = parts[2] if len(parts) >= 3 else raw
            if stem:
                stems.add(stem)
    return stems


# ===== Gate 4 — Final comprehensive approval (Opus multimodal) ===============

def _gate4_final_approval(mp4: Path, spec: dict, episode_dir: Path) -> dict | None:
    """Pre-schedule comprehensive QA via Claude Opus 4.7 multimodal.

    Extracts 6 keyframes, sends with the clip's spec + extracted transcript text
    + scene data. Returns the verdict dict or None on infra error.

    On REJECT: moves clip to _rejected/ + emits Navi.
    On FLAG_FOR_REVIEW: emits Navi but doesn't move (clip stays for human approval).
    On APPROVE: returns verdict; caller continues to upload.
    """
    try:
        from _qa_helpers import (
            call_claude_vision, extract_keyframes, video_duration_sec,
            move_to_rejected, emit_reject_navi, emit_flag_navi,
            log_gate_decision, OPUS_MODEL,
        )
        from qa_prompts import GATE_4_FINAL_APPROVAL_V1
        import json as _json
    except ImportError as exc:
        print(f"  [gate4] qa helpers unavailable ({exc}) — skipping final approval")
        return None

    clip_id = mp4.stem
    duration = video_duration_sec(mp4)
    if duration < 5:
        return {"final_decision": "APPROVE", "reason": "duration < 5s, skipping gate4"}

    # 6 keyframes spread across the clip
    kf_dir = episode_dir / "_kf" / clip_id
    timestamps = [duration * pct for pct in (0.05, 0.20, 0.40, 0.60, 0.80, 0.95)]
    keyframes = extract_keyframes(mp4, timestamps, kf_dir, prefix="g4")
    if len(keyframes) < 4:
        print(f"  [gate4] only {len(keyframes)} keyframes — skipping")
        return None

    # Pull extracted text from the transcript matching the source_stem
    source_stem = spec.get("source_stem", "")
    extracted_text = ""
    word_excerpt = "(unavailable)"
    if source_stem:
        tx_path = ROOT / "data" / "podcast" / "transcripts" / f"{source_stem}.json"
        if tx_path.exists():
            try:
                tx = _json.loads(tx_path.read_text())
                start = float(spec.get("start_sec", 0))
                end = float(spec.get("end_sec", duration))
                parts = []
                first_words = []
                for seg in tx.get("segments", []):
                    if seg["end"] < start:
                        continue
                    if seg["start"] > end:
                        break
                    parts.append(seg["text"].strip())
                    if len(first_words) < 30:
                        for w in (seg.get("words") or []):
                            if len(first_words) >= 30:
                                break
                            first_words.append(w)
                extracted_text = " ".join(parts).strip()[:5000]
                word_excerpt = "\n".join(
                    f"  [{w.get('start', 0):.2f}s] {w.get('word', '').strip()}"
                    for w in first_words
                ) or "(no words)"
            except Exception as exc:
                print(f"  [gate4] transcript read failed: {exc}")

    # Compact scene summary (best-effort — may not be available)
    scenes_summary = "(scene data not available at schedule stage)"

    prompt = GATE_4_FINAL_APPROVAL_V1.format(
        title=spec.get("title", "?"),
        hook=spec.get("hook", "?"),
        topics=", ".join(spec.get("topics", [])) or "?",
        duration_sec=duration,
        scenes_summary=scenes_summary,
        extracted_text=extracted_text or "(transcript unavailable)",
        word_timings_excerpt=word_excerpt,
    )

    try:
        verdict = call_claude_vision(prompt, keyframes, model=OPUS_MODEL, max_tokens=2500)
    except Exception as exc:
        print(f"  [gate4] opus error: {exc} — letting clip through")
        return None

    decision = (verdict.get("final_decision") or "").upper()
    print(f"  [gate4] decision={decision}")

    # Log every Gate 4 decision (APPROVE / FLAG / REJECT)
    log_gate_decision(source_stem, "gate4", clip_id, verdict, extra={
        "duration_sec": duration,
        "n_keyframes": len(keyframes),
    })

    if decision == "REJECT":
        move_to_rejected(mp4, episode_dir, "Gate 4 (final approval)", verdict, clip_id)
        emit_reject_navi(clip_id, "Gate 4 (final approval)", verdict, source_stem)
    elif decision == "FLAG_FOR_REVIEW":
        emit_flag_navi(clip_id, "Gate 4 (final approval)",
                       verdict.get("issues", []) or [], source_stem)
    return verdict


def schedule(episode: str, start_date: str, dry_run: bool = True,
             clips_plan_path: Path = CLIPS_PLAN_ALL,
             strict_titles: bool = False, force: bool = False) -> int:
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

    # --- Dedupe (2026-05-07): skip any clip that already went out OR is queued.
    # The directory glob above can include stale rendered clips from prior
    # episodes that happen to share the folder. Without this gate, every
    # re-run of schedule_shorts.py re-schedules them, producing the duplicate
    # cross-platform posts that prompted this fix.
    if not force:
        posted_stems = _previously_posted_stems()
        try:
            zernio_stems = _scheduled_in_zernio_stems(ZernioClient())
        except Exception:
            zernio_stems = set()
        skip_stems = posted_stems | zernio_stems
        kept: list[Path] = []
        skipped: list[tuple[Path, str]] = []
        for mp4 in mp4s:
            if mp4.name in skip_stems:
                src = "queued" if mp4.name in zernio_stems else "posted"
                skipped.append((mp4, src))
            else:
                kept.append(mp4)
        if skipped:
            print(f"[DEDUPE] {len(skipped)} clip(s) skipped (already {set(s for _,s in skipped)})")
            for mp4, src in skipped:
                print(f"  · {mp4.name}  [{src}]")
            print("  Pass --force to re-schedule anyway.")
        mp4s = kept
        if not mp4s:
            print("[OK] nothing new to schedule (all already posted or queued).")
            return 0

    times = _build_schedule(len(mp4s), start_date)
    print(f"[PLAN] {len(mp4s)} clips · {SLOT_HOURS} ET · starting {start_date}")
    title_warnings: list[tuple[str, list[str]]] = []
    for mp4, when in zip(mp4s, times):
        spec = plan_by_id.get(mp4.stem, {"hook": mp4.stem, "topics": []})
        final_title, warnings = _qa_title(spec)
        display_title = final_title or spec.get("hook", "")[:60]
        flag = " ⚠" if warnings else ""
        print(f"  {when.strftime('%Y-%m-%d %H:%M %Z')}  {mp4.name}  — {display_title}{flag}")
        for w in warnings:
            print(f"      ⚠ {w}")
        if warnings:
            title_warnings.append((mp4.name, warnings))

    if title_warnings:
        print(f"\n[QA] {len(title_warnings)} clip(s) have title issues:")
        for name, warns in title_warnings:
            print(f"  · {name}: {'; '.join(warns)}")
        print("  Fix in data/podcast/clips_plan/<episode>.json (and _all.json), "
              "or re-run pick_clips.py to regenerate.")

    if dry_run:
        print("\n[DRY-RUN] not uploading. Re-run with --execute to push.")
        return 0

    if strict_titles and title_warnings:
        print(f"\n[FATAL] --strict-titles set and {len(title_warnings)} clip(s) failed QA. "
              "Fix titles or re-run without --strict-titles.", file=sys.stderr)
        return 3

    client = ZernioClient()
    accounts = _accounts_by_platform(client)
    missing = [p for p in TARGET_PLATFORMS if p not in accounts]
    if missing:
        print(f"[FATAL] missing Zernio accounts for: {missing}. Connect them at zernio.com/dashboard.",
              file=sys.stderr)
        return 2

    log = []
    gate4_rejected = 0
    gate4_flagged = 0
    for mp4, when in zip(mp4s, times):
        spec = plan_by_id.get(mp4.stem, {"hook": mp4.stem, "topics": []})
        caption = _caption_for(spec)

        # GATE 4 (2026-05-07): final comprehensive QA via Claude Opus 4.7 multimodal.
        # Sends 6 keyframes + spec + transcript + scene data. Routes:
        #   APPROVE         → continue to upload
        #   FLAG_FOR_REVIEW → skip upload, emit Navi for human review
        #   REJECT          → skip upload + move to _rejected/ + emit Navi
        # Failures during QA infrastructure (network, missing keyframes) → let through
        # so we don't block on infra issues.
        g4 = _gate4_final_approval(mp4, spec, episode_clips_dir)
        if g4:
            decision = (g4.get("final_decision") or "").upper()
            if decision == "REJECT":
                gate4_rejected += 1
                log.append({"clip": mp4.name, "gate4": "REJECTED",
                            "reason": g4.get("reason", "?")})
                print(f"[GATE4] REJECT {mp4.name}: {g4.get('reason', '?')}")
                continue
            if decision == "FLAG_FOR_REVIEW":
                gate4_flagged += 1
                log.append({"clip": mp4.name, "gate4": "FLAGGED",
                            "issues": g4.get("issues", [])})
                print(f"[GATE4] FLAG {mp4.name}: held for human review")
                continue
            print(f"[GATE4] APPROVE {mp4.name}")

        try:
            media_url = _upload_file(client, mp4)
            payload = {
                "scheduledFor": when.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z"),
                "timezone": "America/New_York",
                "platforms": [{"platform": p, "accountId": accounts[p]} for p in TARGET_PLATFORMS],
                "mediaItems": [{"url": media_url, "type": "video"}],
                "content": caption,
            }
            resp = client.create_post(payload)
            post_id = (
                (resp or {}).get("_id")
                or (resp or {}).get("id")
                or (resp or {}).get("data", {}).get("_id")
                or (resp or {}).get("data", {}).get("id")
            )
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
    parser.add_argument("--strict-titles", action="store_true",
                        help="Refuse to --execute if any title fails QA (length / words / blocklist)")
    parser.add_argument("--force", action="store_true",
                        help="Bypass dedupe (re-schedule clips even if already posted/queued)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    return schedule(args.episode, args.start_date, dry_run=args.dry_run,
                    clips_plan_path=Path(args.clips_plan),
                    strict_titles=args.strict_titles, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
