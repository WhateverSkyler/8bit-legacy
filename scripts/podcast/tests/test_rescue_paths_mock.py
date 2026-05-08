#!/usr/bin/env python3
"""Validate Gate 2 + Gate 3 rescue paths fire end-to-end.

We don't have a real clip that genuinely fails in a way that triggers either
rescue (Whisper drift / off-frame), so we MOCK call_claude_vision to return
canned verdicts that force each rescue path. Then we verify:

  Gate 2 rescue:
    1st call → recommendation=rerender_with_offset, estimated_offset_sec=0.3
    rescue closure should fire → ASS rewritten with shifted timings + ffmpeg re-runs
    2nd call → recommendation=pass
    final verdict should have _rescued_from_offset=0.3 + recommendation=pass

  Gate 3 rescue:
    1st call → recommendation=reject_reframe
    rescue closure should fire → detect_scenes_and_crops with cut_threshold=0.25 + ffmpeg re-runs
    2nd call → recommendation=pass
    final verdict should have _rescued_from='reject_reframe' + recommendation=pass

Also tests:
  - Gate 2 with offset > 2s → bypasses rescue, REJECTS
  - Gate 2 with rescue rerender failing → REJECTS gracefully
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

P = Path("/Users/tristanaddi1/Projects/8bit-legacy")
load_dotenv(P / "config" / ".env")
sys.path.insert(0, str(P / "scripts" / "podcast"))
sys.path.insert(0, str(P / "scripts"))

# Stub Navi
import navi_alerts
nav_calls = []
def _stub_nav(title, description, priority="medium", source="8bit"):
    nav_calls.append({"title": title, "priority": priority})
    return -1
navi_alerts.emit_navi_task = _stub_nav
import _qa_helpers
_qa_helpers.emit_navi_task = _stub_nav

# Mock call_claude_vision for controlled testing
mock_responses = []  # list of dicts, popped in order
real_call_claude_vision = _qa_helpers.call_claude_vision
def _mock_vision(prompt, image_paths, model="claude-sonnet-4-6", max_tokens=2000, media_type="image/jpeg"):
    if not mock_responses:
        raise RuntimeError("Mock exhausted — gate called more times than expected")
    resp = mock_responses.pop(0)
    print(f"    [mock] returned: {resp.get('recommendation', resp.get('final_decision', '?'))}")
    # Add the standard _meta the real function attaches
    resp = dict(resp)
    resp["_meta"] = {"model": model, "tokens_in": 100, "tokens_out": 30, "latency_ms": 1}
    return resp
_qa_helpers.call_claude_vision = _mock_vision
# Also patch the import inside render_clip
import render_clip
render_clip.call_claude_vision = _mock_vision  # in case it was imported at module level (it's lazy import so this is belt-and-suspenders)

from render_clip import _gate2_caption_sync, _gate3_framing

# Helper to make a fresh sandbox + clip for each test
def make_sandbox(tag):
    tmp = Path(tempfile.mkdtemp(prefix=f"qa-rescue-{tag}-"))
    ep = tmp / "Test_Ep"
    ep.mkdir(parents=True, exist_ok=True)
    src = Path("/tmp/may5-test/clips/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p_c1.mp4")
    target = ep / f"{tag}.mp4"
    shutil.copy(src, target)
    return tmp, ep, target

# Build a fake "render successful" closure that just returns True (we don't actually re-render in mock land)
fake_rerender_called = []
def fake_g2_rerender(offset_sec):
    fake_rerender_called.append(("g2", offset_sec))
    return True  # pretend it worked

def fake_g3_rerender():
    fake_rerender_called.append(("g3", "stricter"))
    new_scenes = [(0.0, 30.0, 200), (30.0, 60.0, 350), (60.0, 84.0, 250)]  # synthetic stricter result
    return True, new_scenes

# Words + spec used across tests
spec = {
    "clip_id": "rescue_test",
    "title": "Test Title",
    "hook": "Test hook",
    "topics": ["test"],
    "source_stem": "test_rescue_episode",
}
words = [
    {"start": 0.5, "end": 1.0, "word": "this"},
    {"start": 1.0, "end": 1.5, "word": "is"},
    {"start": 1.5, "end": 2.0, "word": "test"},
]

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

# Clean any prior test log
log_path = P / "data" / "podcast" / "qa_logs" / "test_rescue_episode.jsonl"
if log_path.exists():
    log_path.unlink()

# ================================================================
# TEST 1: Gate 2 rerender_with_offset (success) → rescue fires → second call passes
# ================================================================
print()
print("=" * 70)
print("TEST 1: Gate 2 rescue — drift (0.3s) → offset rerender → pass")
print("=" * 70)
fake_rerender_called.clear()
nav_calls.clear()
mock_responses.clear()
mock_responses.extend([
    {"recommendation": "rerender_with_offset", "sync_quality": "drift",
     "estimated_offset_sec": 0.3, "issues": ["captions slightly behind"],
     "reason": "minor caption drift"},
    {"recommendation": "pass", "sync_quality": "good",
     "issues": [], "reason": "good after offset"},
])
tmp, ep, clip = make_sandbox("t1")
duration = 84.0  # we don't really render, this is just metadata
verdict = _gate2_caption_sync(clip, words, spec, duration, ep, "rescue_test",
                              rerender_func=fake_g2_rerender)
check("rescue closure was called", len(fake_rerender_called) == 1)
check("rescue called with offset=0.3", fake_rerender_called and fake_rerender_called[0] == ("g2", 0.3))
check("final verdict is pass", (verdict.get("recommendation") or "").lower() == "pass")
check("_rescued_from_offset attached", verdict.get("_rescued_from_offset") == 0.3)
check("no Navi calls (rescue succeeded)", len(nav_calls) == 0)
check("no _rejected/ created", not (ep / "_rejected").exists())
check("clip still in place (not moved)", clip.exists())

# ================================================================
# TEST 2: Gate 2 with offset > 2s → out-of-bounds → REJECT (no rescue)
# ================================================================
print()
print("=" * 70)
print("TEST 2: Gate 2 with offset 3.5s → out-of-bounds → REJECT")
print("=" * 70)
fake_rerender_called.clear()
nav_calls.clear()
mock_responses.clear()
mock_responses.append({
    "recommendation": "rerender_with_offset", "sync_quality": "misaligned",
    "estimated_offset_sec": 3.5,
    "issues": ["wildly off"], "reason": "huge drift"})
tmp, ep, clip = make_sandbox("t2")
verdict = _gate2_caption_sync(clip, words, spec, duration, ep, "rescue_test",
                              rerender_func=fake_g2_rerender)
check("rescue NOT called for out-of-bounds offset", len(fake_rerender_called) == 0)
check("verdict became REJECT", (verdict.get("recommendation") or "").lower() == "reject")
check("_rescue_skipped reason attached", "_rescue_skipped" in verdict)
check("clip moved to _rejected/", (ep / "_rejected" / "t2.mp4").exists())
check("Navi reject task fired", any(c.get("priority") == "high" for c in nav_calls))

# ================================================================
# TEST 3: Gate 2 rescue rerender FAILS → graceful REJECT
# ================================================================
print()
print("=" * 70)
print("TEST 3: Gate 2 rescue — drift → rerender returns False → REJECT")
print("=" * 70)
fake_rerender_called.clear()
nav_calls.clear()
mock_responses.clear()
mock_responses.append({
    "recommendation": "rerender_with_offset", "sync_quality": "drift",
    "estimated_offset_sec": 0.5,
    "issues": ["drift"], "reason": "drift"})
def failing_rerender(offset_sec):
    fake_rerender_called.append(("g2", offset_sec))
    return False  # simulate ffmpeg failure
tmp, ep, clip = make_sandbox("t3")
verdict = _gate2_caption_sync(clip, words, spec, duration, ep, "rescue_test",
                              rerender_func=failing_rerender)
check("rescue rerender was attempted", len(fake_rerender_called) == 1)
check("verdict became REJECT after failure", (verdict.get("recommendation") or "").lower() == "reject")
check("_rescue_failed flag set", verdict.get("_rescue_failed") is True)
check("clip moved to _rejected/", (ep / "_rejected" / "t3.mp4").exists())

# ================================================================
# TEST 4: Gate 3 reject_reframe (success) → stricter scenes → second call passes
# ================================================================
print()
print("=" * 70)
print("TEST 4: Gate 3 rescue — reject_reframe → stricter scenes → pass")
print("=" * 70)
fake_rerender_called.clear()
nav_calls.clear()
mock_responses.clear()
mock_responses.extend([
    {"recommendation": "reject_reframe", "overall_quality": "poor",
     "frames": [{"pct": 25, "subject_position": "off_frame", "issue": "speaker cut"}],
     "transitions": [], "reason": "frame issues"},
    {"recommendation": "pass", "overall_quality": "good",
     "frames": [], "transitions": [], "reason": "good after stricter detection"},
])
tmp, ep, clip = make_sandbox("t4")
scenes = [(0.0, duration, 656)]  # initial scenes — single center crop
verdict = _gate3_framing(clip, scenes, duration, spec, ep, "rescue_test",
                         rerender_func=fake_g3_rerender)
check("rescue closure was called", len(fake_rerender_called) == 1)
check("rescue called for stricter detection",
      fake_rerender_called and fake_rerender_called[0] == ("g3", "stricter"))
check("final verdict is pass",  (verdict.get("recommendation") or "").lower() == "pass")
check("_rescued_from attached", verdict.get("_rescued_from") == "reject_reframe")
check("_new_scene_count attached", verdict.get("_new_scene_count") == 3)
check("no _rejected/ created (rescued)", not (ep / "_rejected").exists())

# ================================================================
# TEST 5: Gate 3 rescue still fails → REJECT propagated
# ================================================================
print()
print("=" * 70)
print("TEST 5: Gate 3 rescue — reject_reframe → stricter scenes → still reject")
print("=" * 70)
fake_rerender_called.clear()
nav_calls.clear()
mock_responses.clear()
mock_responses.extend([
    {"recommendation": "reject_reframe", "overall_quality": "poor",
     "frames": [{"pct": 25, "subject_position": "off_frame", "issue": "?"}],
     "transitions": [], "reason": "frame issues"},
    {"recommendation": "reject", "overall_quality": "poor",
     "frames": [{"pct": 50, "subject_position": "off_frame", "issue": "still bad"}],
     "transitions": [], "reason": "stricter detection didn't help"},
])
tmp, ep, clip = make_sandbox("t5")
verdict = _gate3_framing(clip, [(0.0, duration, 656)], duration, spec, ep, "rescue_test",
                         rerender_func=fake_g3_rerender)
check("rescue was attempted", len(fake_rerender_called) == 1)
check("final verdict is reject", (verdict.get("recommendation") or "").lower() == "reject")
check("clip moved to _rejected/ via retry", (ep / "_rejected").exists())

# ================================================================
# Final summary
# ================================================================
print()
print("=" * 70)
print(f"RESCUE PATH VALIDATION: {ok} passed, {fail} failed")
print("=" * 70)

# Cleanup the test log
if log_path.exists():
    print(f"\nQA log entries written: {len(log_path.read_text().splitlines())}")
    log_path.unlink()

# Restore real call_claude_vision
_qa_helpers.call_claude_vision = real_call_claude_vision
sys.exit(0 if fail == 0 else 1)
