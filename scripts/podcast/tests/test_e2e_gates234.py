#!/usr/bin/env python3
"""Phase 1B E2E: Run Gates 2 → 3 → 4 on a single real rendered MP4.
Validates the full pipeline integration: keyframe extraction, multimodal API,
log writing, decision routing — all on real data, not synthetic.

Uses the May 5 V2 c1 clip already pulled to /tmp/may5-test/clips/.
"""
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from dotenv import load_dotenv

P = Path("/Users/tristanaddi1/Projects/8bit-legacy")
load_dotenv(P / "config" / ".env")
sys.path.insert(0, str(P / "scripts" / "podcast"))
sys.path.insert(0, str(P / "scripts"))

# Stub Navi to capture calls instead of firing them
import navi_alerts
nav_calls = []
def _stub(title, description, priority="medium", source="8bit"):
    nav_calls.append({"title": title, "priority": priority})
    return -1
navi_alerts.emit_navi_task = _stub
import _qa_helpers
_qa_helpers.emit_navi_task = _stub

from render_clip import _gate2_caption_sync, _gate3_framing, detect_scenes_and_crops, _words_in_range
from schedule_shorts import _gate4_final_approval
from _qa_helpers import video_duration_sec

# Sandbox so we don't pollute real data
tmp = Path(tempfile.mkdtemp(prefix="qa-e2e-"))
sandbox_episode = tmp / "Test_Ep"
sandbox_episode.mkdir(parents=True, exist_ok=True)

src_clip = Path("/tmp/may5-test/clips/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p_c1.mp4")
test_clip = sandbox_episode / "test_e2e_c1.mp4"
shutil.copy(src_clip, test_clip)

# Need a transcript for Gate 4 — copy the May 5 transcript over to expected location
real_tx = Path("/tmp/may5-test/transcripts/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.json")
sandbox_tx_dir = P / "data" / "podcast" / "transcripts"
sandbox_tx_dir.mkdir(parents=True, exist_ok=True)
sandbox_tx_path = sandbox_tx_dir / "test_e2e_source.json"
if not sandbox_tx_path.exists():
    shutil.copy(real_tx, sandbox_tx_path)

duration = video_duration_sec(test_clip)
spec = {
    "clip_id": "test_e2e_c1",
    "title": "The Assassin's Creed Black Flag Pricing Debate",
    "hook": "Black Flag is one of the best Assassin's Creed games",
    "topics": ["Black Flag", "pricing", "Ubisoft"],
    "source_stem": "test_e2e_source",
    "start_sec": 0.0,
    "end_sec": duration,
}

print("=" * 70)
print(f"E2E GATE TEST — {test_clip.name}")
print(f"Duration: {duration:.1f}s")
print(f"Sandbox: {tmp}")
print("=" * 70)

# Need words for Gate 2; build via _words_in_range from the real transcript
tx = json.loads(real_tx.read_text())
words = _words_in_range(tx, 0.0, duration)
print(f"Loaded {len(words)} words from transcript for the [0, {duration:.0f}s] range")

# Need scenes for Gate 3; run real detection
print(f"\nRunning detect_scenes_and_crops...")
t_scene = time.time()
scenes = detect_scenes_and_crops(Path("/tmp/may5-test/clips/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p_c1.mp4"),
                                  0.0, duration)
print(f"  detected {len(scenes)} scenes in {time.time()-t_scene:.1f}s")

# Reset the QA log file
log_path = P / "data" / "podcast" / "qa_logs" / "test_e2e_source.jsonl"
if log_path.exists():
    log_path.unlink()

# === Gate 2 ===
print()
print("─── Gate 2 (caption sync) ─────")
t = time.time()
g2 = _gate2_caption_sync(test_clip, words, spec, duration, sandbox_episode, "test_e2e_c1")
print(f"  elapsed: {time.time()-t:.1f}s")
print(f"  recommendation: {g2.get('recommendation') if g2 else None}")
print(f"  reason: {(g2.get('reason') if g2 else None)[:120]}")

# === Gate 3 ===
print()
print("─── Gate 3 (framing) ──────────")
t = time.time()
g3 = _gate3_framing(test_clip, scenes, duration, spec, sandbox_episode, "test_e2e_c1")
print(f"  elapsed: {time.time()-t:.1f}s")
print(f"  recommendation: {g3.get('recommendation') if g3 else None}")
print(f"  reason: {(g3.get('reason') if g3 else None)[:120]}")

# === Gate 4 ===
print()
print("─── Gate 4 (final approval, Opus) ──")
t = time.time()
g4 = _gate4_final_approval(test_clip, spec, sandbox_episode)
print(f"  elapsed: {time.time()-t:.1f}s")
print(f"  final_decision: {g4.get('final_decision') if g4 else None}")
print(f"  reason: {(g4.get('reason') if g4 else None)[:200]}")

# === Inspect QA log ===
print()
print("=" * 70)
print("QA LOG INSPECTION")
print("=" * 70)
if log_path.exists():
    lines = log_path.read_text().strip().split("\n")
    print(f"Wrote {len(lines)} entries to {log_path.name}:")
    total_cost = 0
    total_tokens_in = 0
    total_tokens_out = 0
    total_latency_ms = 0
    for line in lines:
        rec = json.loads(line)
        total_cost += rec.get("cost_usd", 0)
        total_tokens_in += rec.get("tokens_in", 0)
        total_tokens_out += rec.get("tokens_out", 0)
        total_latency_ms += rec.get("latency_ms", 0)
        print(f"  [{rec['gate']:<10}] {rec['model']:<22} "
              f"tin={rec['tokens_in']:>6} tout={rec['tokens_out']:>4} "
              f"lat={rec['latency_ms']:>5}ms ${rec['cost_usd']:.4f}")
    print(f"\n  TOTAL: {total_tokens_in:,} in + {total_tokens_out:,} out, "
          f"{total_latency_ms/1000:.1f}s wall, ${total_cost:.4f}")
    # Cleanup the test log so we don't leave artifacts
    log_path.unlink()
else:
    print("  No log file written!")

# === Inspect Navi calls ===
print()
print("=" * 70)
print(f"NAVI CALLS: {len(nav_calls)}")
for c in nav_calls:
    print(f"  [{c['priority']}] {c['title']}")

# Cleanup the synthetic transcript
sandbox_tx_path.unlink()
print()
print(f"Sandbox preserved at: {tmp}")
