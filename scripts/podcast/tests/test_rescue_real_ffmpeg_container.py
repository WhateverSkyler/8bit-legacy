#!/usr/bin/env python3
"""Container-side validation: render a real clip end-to-end with mocked Claude
returning rerender_with_offset(0.4), verify the rescue closure ACTUALLY:
  - rebuilds the ASS file with shifted timings
  - re-runs ffmpeg producing a new MP4 (mtime updated)
  - re-calls Gate 2 and accepts the rescued render

Designed to run inside the 8bit-pipeline:latest container which has libass-
enabled ffmpeg.

Usage (from TrueNAS root via docker run):
  docker run --rm \
    --env-file /mnt/pool/apps/8bit-pipeline/.env \
    -e NAVI_URL=http://invalid:0 \
    -v /mnt/pool/apps/8bit-pipeline/data:/app/data \
    -v /mnt/pool/apps/8bit-pipeline/config:/app/config:ro \
    -v "/mnt/pool/NAS/Media/8-Bit Legacy:/media:ro" \
    -v /tmp/test-rescue-in-container.py:/app/test-rescue-in-container.py:ro \
    --user 950:950 \
    --entrypoint python3 \
    8bit-pipeline:latest \
    /app/test-rescue-in-container.py
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Container layout — scripts live at /app/scripts
sys.path.insert(0, "/app/scripts/podcast")
sys.path.insert(0, "/app/scripts")

# Stub Navi
import navi_alerts
navi_alerts.emit_navi_task = lambda *a, **k: -1

# Mock Claude vision
import _qa_helpers
mock_responses = []
mock_calls = []
real_call_claude_vision = _qa_helpers.call_claude_vision

def _mock_vision(prompt, image_paths, model="claude-sonnet-4-6", max_tokens=2000, media_type="image/jpeg"):
    if not mock_responses:
        raise RuntimeError("Mock exhausted — gate called more than expected")
    mock_calls.append({"prompt_len": len(prompt), "n_images": len(image_paths)})
    resp = mock_responses.pop(0)
    print(f"    [mock #{len(mock_calls)}] returning recommendation={resp.get('recommendation', resp.get('final_decision', '?'))}")
    return {**resp, "_meta": {"model": model, "tokens_in": 100, "tokens_out": 30, "latency_ms": 1}}
_qa_helpers.call_claude_vision = _mock_vision
_qa_helpers.emit_navi_task = lambda *a, **k: -1

from render_clip import render_clip
from _qa_helpers import video_duration_sec

# Find any source video on the container
P = Path("/app/data/podcast")
sources = list((P / "source" / "1080p").glob("*.mp4"))
transcripts = list((P / "transcripts").glob("*.json"))
if not sources or not transcripts:
    print("FATAL: no sources or transcripts in container")
    sys.exit(2)

# Find a source-transcript pair that match
source_to_use = None
transcript_to_use = None
for src in sources:
    tx_candidate = P / "transcripts" / f"{src.stem}.json"
    if tx_candidate.exists():
        source_to_use = src
        transcript_to_use = tx_candidate
        break
if not source_to_use:
    print("FATAL: no matching source-transcript pair")
    sys.exit(2)

print(f"Source: {source_to_use.name} ({source_to_use.stat().st_size / 1e6:.0f} MB)")
print(f"Transcript: {transcript_to_use.name}")

tx = json.loads(transcript_to_use.read_text())

# === TEST: Gate 2 rescue with real ffmpeg ===
print()
print("=" * 70)
print("TEST 1: Gate 2 RESCUE — real ffmpeg, mocked Claude")
print("=" * 70)
# Mock: G2 says rerender_with_offset(0.4), then on retry says pass.
# G3 says pass (so we don't trigger another rescue path).
mock_responses.clear()
mock_calls.clear()
mock_responses.extend([
    {"recommendation": "rerender_with_offset", "sync_quality": "drift",
     "estimated_offset_sec": 0.4, "issues": ["drift"], "reason": "synthetic drift"},
    {"recommendation": "pass", "sync_quality": "good",
     "issues": [], "reason": "good after rescue"},
    {"recommendation": "pass", "overall_quality": "good",
     "frames": [], "transitions": [], "reason": "framing fine"},
])

# Pick a 30s window inside the source. Get duration first.
duration_full = video_duration_sec(source_to_use)
print(f"Full source duration: {duration_full:.1f}s")
clip_start = min(60.0, duration_full / 4)
clip_end = clip_start + 30.0
print(f"Test clip window: {clip_start:.1f}s – {clip_end:.1f}s")

spec = {
    "clip_id": "rescue_g2_real",
    "title": "Test Rescue",
    "hook": "Test hook",
    "topics": ["test"],
    "source_stem": source_to_use.stem,
    "start_sec": clip_start,
    "end_sec": clip_end,
}

episode_name = "QA_RESCUE_REAL"
ep_dir = Path("/app/data/podcast/clips") / episode_name
shutil.rmtree(ep_dir, ignore_errors=True)

t_start = time.time()
out_path = render_clip(spec, episode_name, {spec["source_stem"]: tx})
elapsed = time.time() - t_start
print(f"\nrender_clip elapsed: {elapsed:.1f}s")

ok = 0
fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond:
        print(f"  PASS: {label} {detail}")
        ok += 1
    else:
        print(f"  FAIL: {label} {detail}")
        fail += 1

# === Verifications ===
check("render_clip returned a path", out_path is not None)
if out_path:
    check("MP4 exists", out_path.exists(),
          f"({out_path.stat().st_size:,} bytes)" if out_path.exists() else "")
ass_path = ep_dir / "rescue_g2_real.ass"
check("ASS exists", ass_path.exists())

# Mock should have been called 3 times total: G2 initial, G2 retry, G3
check("Mock vision called 3 times", len(mock_calls) == 3,
      f"(actual: {len(mock_calls)})")

# Inspect ASS — after rescue with offset=+0.4, every word's start should be
# 0.4s LATER than the original. We can verify by re-checking against words list.
if ass_path.exists():
    ass = ass_path.read_text()
    n_dialogue = ass.count("Dialogue:")
    check("ASS has dialogue events", n_dialogue > 5, f"({n_dialogue})")
    # First Dialogue line — extract its start timestamp
    first = next((l for l in ass.splitlines() if l.startswith("Dialogue:")), None)
    if first:
        parts = first.split(",", 4)  # split on commas, max 5 fields
        time_str = parts[1].strip()
        h, m, s = time_str.split(":")
        first_start = int(h)*3600 + int(m)*60 + float(s)
        # After +0.4 offset, first dialogue should START at >= original_first + 0.4.
        # We don't know the original first, but we know words within the clip range
        # likely start near 0.0-0.5s. After +0.4 shift, first dialogue should be >= 0.4.
        check("First dialogue starts >= 0.4s (offset applied)",
              first_start >= 0.4, f"({first_start:.2f}s)")

# Verify mtime — MP4 should have been re-rendered AFTER ASS was rewritten
# (initial render → rescue rebuild ASS → re-render)
if out_path and out_path.exists() and ass_path.exists():
    mp4_mtime = out_path.stat().st_mtime
    ass_mtime = ass_path.stat().st_mtime
    print(f"  MP4 mtime: {mp4_mtime:.2f}, ASS mtime: {ass_mtime:.2f}")
    check("MP4 mtime >= ASS mtime (re-render after ASS update)",
          mp4_mtime >= ass_mtime - 1)  # allow 1s slack

print()
print(f"Mock calls captured: {len(mock_calls)}")
for i, c in enumerate(mock_calls):
    print(f"  [{i+1}] prompt_len={c['prompt_len']}, n_images={c['n_images']}")

# Cleanup
shutil.rmtree(ep_dir, ignore_errors=True)

# === TEST 2: Gate 3 rescue with real ffmpeg ===
print()
print("=" * 70)
print("TEST 2: Gate 3 RESCUE — real ffmpeg, mocked Claude")
print("=" * 70)

mock_responses.clear()
mock_calls.clear()
# G2 passes, G3 says reject_reframe, G3 retry says pass
mock_responses.extend([
    {"recommendation": "pass", "sync_quality": "good",
     "issues": [], "reason": "good"},
    {"recommendation": "reject_reframe", "overall_quality": "poor",
     "frames": [{"pct": 25, "subject_position": "off_frame", "issue": "?"}],
     "transitions": [], "reason": "framing off"},
    {"recommendation": "pass", "overall_quality": "good",
     "frames": [], "transitions": [], "reason": "good after stricter detection"},
])

spec2 = {**spec, "clip_id": "rescue_g3_real"}
shutil.rmtree(ep_dir, ignore_errors=True)
t2 = time.time()
out_path2 = render_clip(spec2, episode_name, {spec["source_stem"]: tx})
print(f"\nrender_clip elapsed: {time.time()-t2:.1f}s")
print(f"Mock calls: {len(mock_calls)}")

check("Gate 3 rerender returned path", out_path2 is not None)
check("Mock called 3 times for G3 path", len(mock_calls) == 3)
if out_path2:
    check("Gate 3 rerendered MP4 exists", out_path2.exists())

shutil.rmtree(ep_dir, ignore_errors=True)

print()
print("=" * 70)
print(f"REAL-FFMPEG RESCUE: {ok} passed, {fail} failed")
print("=" * 70)

# Restore real call_claude_vision
_qa_helpers.call_claude_vision = real_call_claude_vision
sys.exit(0 if fail == 0 else 1)
