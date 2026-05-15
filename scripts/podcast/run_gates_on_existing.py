#!/usr/bin/env python3
"""Run Gates 2 + 3 + 4 against an existing folder of rendered shorts.

Use cases:
  - Multi-sample validation across diverse content (April + May)
  - Re-validate May 5 clips through the new gates without re-rendering
  - Smoke-test a new prompt version on past content
  - Estimate per-episode QA cost on real-shape content

Doesn't render anything — operates on .mp4 files already on disk. Doesn't
publish anything — Gate 4 routes any rejects to <episode>/_rejected_test/
(separate from production _rejected/) so this tool is non-destructive.

Usage:
  python3 scripts/podcast/run_gates_on_existing.py "Episode_May_5_2026"
  python3 scripts/podcast/run_gates_on_existing.py --episode-dir /path/to/Episode_X --max 5

Requires: data/podcast/clips_plan/_all.json (for clip metadata) +
          data/podcast/transcripts/<source_stem>.json (for words / scenes ref)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "podcast"))

CLIPS_DIR = ROOT / "data" / "podcast" / "clips"
TRANSCRIPTS = ROOT / "data" / "podcast" / "transcripts"
PLANS_DIR = ROOT / "data" / "podcast" / "clips_plan"


def _load_clip_specs() -> dict[str, dict]:
    """Load _all.json and return {clip_id: spec}."""
    all_path = PLANS_DIR / "_all.json"
    if not all_path.exists():
        return {}
    return {c["clip_id"]: c for c in json.loads(all_path.read_text())}


def _load_transcript(source_stem: str) -> dict | None:
    p = TRANSCRIPTS / f"{source_stem}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def _temp_isolation_dir(episode_dir: Path) -> Path:
    """Run rejected files into a TEST-ONLY subdir so production rejects aren't
    confused with multi-sample-test rejects."""
    test_dir = episode_dir.parent / f"{episode_dir.name}__qa_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Gates 2+3+4 on existing rendered shorts")
    parser.add_argument("episode_name", nargs="?",
                        help="Folder under data/podcast/clips/ to process")
    parser.add_argument("--episode-dir", help="Explicit absolute path to episode dir")
    parser.add_argument("--max", type=int, default=0,
                        help="Cap on # of clips to process (0 = all)")
    parser.add_argument("--skip-gate4", action="store_true",
                        help="Skip the expensive Opus Gate 4 call")
    parser.add_argument("--gate4-only", action="store_true",
                        help="Run only Gate 4 (skip 2+3)")
    parser.add_argument("--non-destructive", action="store_true", default=True,
                        help="Route rejects to _rejected__qa_test/ instead of production _rejected/")
    args = parser.parse_args()

    # Resolve episode dir
    if args.episode_dir:
        ep_dir = Path(args.episode_dir)
    elif args.episode_name:
        ep_dir = CLIPS_DIR / args.episode_name
    else:
        parser.error("pass episode_name or --episode-dir")
    if not ep_dir.is_dir():
        print(f"[FATAL] not a directory: {ep_dir}", file=sys.stderr)
        return 2

    # Use a sandbox dir for any moves so we don't pollute production _rejected/
    sandbox_dir = _temp_isolation_dir(ep_dir) if args.non_destructive else ep_dir

    # Find all rendered clips
    mp4s = sorted(p for p in ep_dir.glob("*.mp4") if not p.name.startswith("_"))
    if args.max:
        mp4s = mp4s[:args.max]
    print(f"Episode: {ep_dir.name}")
    print(f"Found {len(mp4s)} rendered clips")
    print(f"Sandbox (rejects go here): {sandbox_dir}")
    print()

    # Hard-link each production clip into the sandbox so the gate code's
    # move_to_rejected only moves the LINK — the production original stays put.
    # Falls back to copy if hard-link fails (cross-device, perms).
    import os as _os
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    for mp4 in mp4s:
        target = sandbox_dir / mp4.name
        if target.exists() and target.stat().st_size == mp4.stat().st_size:
            staged.append(target)
            continue
        try:
            if target.exists():
                target.unlink()
            _os.link(mp4, target)
        except OSError:
            shutil.copy(mp4, target)
        staged.append(target)
    print(f"Staged {len(staged)} clips into sandbox (hard-links if same fs)")
    print()
    mp4s = staged  # iterate over the staged copies, not production paths

    # Lazy imports — keep module-load fast
    from render_clip import _gate2_caption_sync, _gate3_framing, detect_scenes_and_crops, _words_in_range
    from schedule_shorts import _gate4_final_approval
    from _qa_helpers import video_duration_sec

    specs = _load_clip_specs()
    print(f"Loaded {len(specs)} clip specs from _all.json")

    transcripts: dict[str, dict] = {}

    results: list[dict] = []
    t_total = time.time()

    for i, mp4 in enumerate(mp4s, 1):
        clip_id = mp4.stem
        spec = specs.get(clip_id) or {
            "clip_id": clip_id, "title": clip_id, "hook": "?", "topics": [],
            "source_stem": clip_id.rsplit("_c", 1)[0] if "_c" in clip_id else clip_id,
            "start_sec": 0.0, "end_sec": video_duration_sec(mp4),
        }
        source_stem = spec.get("source_stem", "unknown")

        if source_stem not in transcripts:
            tx = _load_transcript(source_stem)
            transcripts[source_stem] = tx or {}
        tx = transcripts[source_stem]

        duration = video_duration_sec(mp4)
        if duration < 5:
            print(f"[{i}/{len(mp4s)}] {clip_id}: duration {duration:.1f}s — skipping")
            continue

        words = _words_in_range(tx, float(spec.get("start_sec", 0)),
                                float(spec.get("end_sec", duration))) if tx else []
        # If words come from offset bounds (e.g., re-rendered after Gate 1 adjust),
        # they're relative to start_sec. For an existing clip we need 0-relative.
        if words and words[0].get("start", 0) > 5:
            # words are likely absolute from transcript — shift to 0-relative
            offset = float(spec.get("start_sec", 0))
            words = [{"start": max(0, w["start"] - offset),
                      "end": max(0, w["end"] - offset),
                      "word": w["word"]} for w in words]

        print(f"[{i}/{len(mp4s)}] {clip_id}  {duration:.1f}s  words={len(words)}  src={source_stem[:40]}")

        clip_result = {
            "clip_id": clip_id,
            "duration_sec": duration,
            "source_stem": source_stem,
            "words_count": len(words),
            "g2": None, "g3": None, "g4": None,
            "elapsed_total_sec": 0,
            "final_status": "?",
        }
        t_clip = time.time()

        # Compute scenes — needed for Gate 3 + display
        if not args.gate4_only:
            try:
                scenes = detect_scenes_and_crops(mp4, 0.0, duration)
                clip_result["scenes_count"] = len(scenes)
            except Exception as exc:
                print(f"  [scenes] failed: {exc} — using single-scene fallback")
                scenes = [(0.0, duration, 656)]
                clip_result["scenes_count"] = 1
        else:
            scenes = [(0.0, duration, 656)]

        # Gate 2
        if not args.gate4_only:
            try:
                g2 = _gate2_caption_sync(mp4, words, spec, duration, sandbox_dir, clip_id)
                clip_result["g2"] = (g2.get("recommendation") if g2 else None) or "skipped"
                if g2 and (g2.get("recommendation") or "").lower() == "reject":
                    clip_result["final_status"] = "REJECTED@gate2"
                    clip_result["elapsed_total_sec"] = round(time.time() - t_clip, 1)
                    results.append(clip_result)
                    print(f"  → REJECTED @ Gate 2 — {g2.get('reason','?')[:80]}")
                    continue
            except Exception as exc:
                print(f"  [gate2] error: {exc}")
                clip_result["g2"] = f"error: {exc}"

        # If clip was moved during gate2 reject, re-resolve path
        if not mp4.exists():
            print(f"  [move] clip moved to _rejected/ during gate, skipping further gates")
            results.append(clip_result)
            continue

        # Gate 3
        if not args.gate4_only:
            try:
                g3 = _gate3_framing(mp4, scenes, duration, spec, sandbox_dir, clip_id)
                clip_result["g3"] = (g3.get("recommendation") if g3 else None) or "skipped"
                if g3 and (g3.get("recommendation") or "").lower() in ("reject", "reject_reframe"):
                    clip_result["final_status"] = f"REJECTED@gate3({g3.get('recommendation')})"
                    clip_result["elapsed_total_sec"] = round(time.time() - t_clip, 1)
                    results.append(clip_result)
                    print(f"  → REJECTED @ Gate 3 — {g3.get('reason','?')[:80]}")
                    continue
            except Exception as exc:
                print(f"  [gate3] error: {exc}")
                clip_result["g3"] = f"error: {exc}"

        if not mp4.exists():
            print(f"  [move] clip moved to _rejected/ during gate, skipping further gates")
            results.append(clip_result)
            continue

        # Gate 4
        if not args.skip_gate4:
            try:
                g4 = _gate4_final_approval(mp4, spec, sandbox_dir)
                clip_result["g4"] = (g4.get("final_decision") if g4 else None) or "skipped"
                if g4:
                    decision = (g4.get("final_decision") or "").upper()
                    if decision == "REJECT":
                        clip_result["final_status"] = "REJECTED@gate4"
                        clip_result["g4_reason"] = g4.get("reason", "?")[:200]
                        print(f"  → REJECTED @ Gate 4 — {g4.get('reason','?')[:80]}")
                    elif decision == "FLAG_FOR_REVIEW":
                        clip_result["final_status"] = "FLAGGED@gate4"
                        clip_result["g4_reason"] = g4.get("reason", "?")[:200]
                        print(f"  → FLAGGED @ Gate 4 — {g4.get('reason','?')[:80]}")
                    elif decision == "APPROVE":
                        clip_result["final_status"] = "APPROVED"
                        print(f"  → APPROVED")
            except Exception as exc:
                print(f"  [gate4] error: {exc}")
                clip_result["g4"] = f"error: {exc}"
        else:
            clip_result["final_status"] = "PASSED@2+3 (gate4 skipped)"

        clip_result["elapsed_total_sec"] = round(time.time() - t_clip, 1)
        results.append(clip_result)

    elapsed = time.time() - t_total
    print()
    print("=" * 70)
    print(f"COMPLETE — {len(results)} clips in {elapsed:.0f}s")
    print("=" * 70)

    # Tally
    status_counts: dict[str, int] = {}
    for r in results:
        status_counts[r["final_status"]] = status_counts.get(r["final_status"], 0) + 1

    print("\nStatus distribution:")
    for s, n in sorted(status_counts.items()):
        print(f"  {s:<35} {n:>3}")

    # Save the report next to the episode
    report_path = sandbox_dir / "qa_test_report.json"
    report_path.write_text(json.dumps({
        "episode": ep_dir.name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_sec": round(elapsed, 1),
        "n_clips": len(results),
        "status_counts": status_counts,
        "results": results,
    }, indent=2, default=str))
    print(f"\nFull report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
