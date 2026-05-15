#!/usr/bin/env python3
"""Verify Gate 1 parallelization preserves order + correctness.

Mocks call_claude_text_async to return predetermined verdicts per candidate,
verifies:
  - Verdicts come back attached to the right candidates (no scrambling)
  - REJECTs are dropped, ADJUSTs apply boundaries, PASSes pass through
  - Concurrent execution is faster than sequential (real timing test)
"""
import asyncio
import json
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

P = Path("/Users/tristanaddi1/Projects/8bit-legacy")
load_dotenv(P / "config" / ".env")
sys.path.insert(0, str(P / "scripts" / "podcast"))
sys.path.insert(0, str(P / "scripts"))

# Mock the async Claude call — return canned verdicts in order, simulate I/O delay
import _qa_helpers
mock_verdicts = []  # popped in order
mock_call_log = []

async def _mock_async_text(prompt, model=None, max_tokens=None, retry_hint=None):
    if not mock_verdicts:
        raise RuntimeError("Mock exhausted")
    # Simulate ~2s of network latency
    await asyncio.sleep(2.0)
    v = mock_verdicts.pop(0)
    mock_call_log.append({"prompt_hash": hash(prompt) % 10000})
    return {**v, "_meta": {"model": "claude-sonnet-4-6", "tokens_in": 100, "tokens_out": 30, "latency_ms": 2000}}

_qa_helpers.call_claude_text_async = _mock_async_text

# Stub navi
import navi_alerts
navi_alerts.emit_navi_task = lambda *a, **k: -1
_qa_helpers.emit_navi_task = lambda *a, **k: -1

from pick_clips import _gate1_narrative_coherence

# Build 6 fake candidates with different verdicts predetermined
candidates = [
    {"clip_id": f"c{i+1}", "title": f"Title {i+1}", "hook": "?", "topics": ["test"],
     "source_stem": "test_async", "start_sec": float(i*30), "end_sec": float(i*30 + 30)}
    for i in range(6)
]

# Build a minimal transcript that has enough text for each candidate range
transcript = {
    "segments": [
        {"start": float(i*30), "end": float(i*30 + 30),
         "text": f"This is candidate {i+1}'s discussion. It contains enough words to pass the 50-character minimum for Gate 1 evaluation. We discuss interesting topics and have a complete arc with a clear conclusion at the end."}
        for i in range(6)
    ]
}

# Predetermined verdicts in order — verify they get applied to the RIGHT candidates
mock_verdicts.extend([
    {"decision": "PASS", "reason": "good", "hook_in_first_5_sec": True, "engagement_risk": "low", "issues": []},   # c1
    {"decision": "REJECT", "reason": "no hook", "hook_in_first_5_sec": False, "engagement_risk": "high", "issues": ["weak"]},  # c2 → drop
    {"decision": "PASS", "reason": "good", "hook_in_first_5_sec": True, "engagement_risk": "low", "issues": []},   # c3
    {"decision": "ADJUST", "reason": "extend",
     "adjusted_boundaries": {"start_sec": 90.0, "end_sec": 130.0},
     "hook_in_first_5_sec": True, "engagement_risk": "low", "issues": []},  # c4 → adjusted
    {"decision": "REJECT", "reason": "exposition only", "hook_in_first_5_sec": False, "engagement_risk": "high", "issues": []},  # c5 → drop
    {"decision": "PASS", "reason": "fine", "hook_in_first_5_sec": True, "engagement_risk": "medium", "issues": []},  # c6
])

# Reset log file
log_path = P / "data" / "podcast" / "qa_logs" / "test_async.jsonl"
if log_path.exists(): log_path.unlink()

# Run Gate 1 — measure wall time
print(f"Running Gate 1 on {len(candidates)} candidates with mocked 2s/call latency...")
print(f"  Sequential would be: ~{len(candidates) * 2}s")
print(f"  Concurrent should be: ~2-3s")
t0 = time.time()
accepted = _gate1_narrative_coherence(candidates, transcript, transcript["segments"])
elapsed = time.time() - t0
print(f"\n  Actual elapsed: {elapsed:.1f}s")

# Verify
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

check("concurrent runtime < 5s", elapsed < 5.0, f"({elapsed:.1f}s)")
check("4 candidates accepted (c1, c3, c4, c6)", len(accepted) == 4, f"({len(accepted)})")
ids = [c["clip_id"] for c in accepted]
check("c1 in accepted", "c1" in ids)
check("c2 NOT in accepted (rejected)", "c2" not in ids)
check("c3 in accepted", "c3" in ids)
check("c4 in accepted (adjusted)", "c4" in ids)
check("c5 NOT in accepted (rejected)", "c5" not in ids)
check("c6 in accepted", "c6" in ids)

# Verify c4 got the adjusted boundaries
c4 = next((c for c in accepted if c["clip_id"] == "c4"), None)
if c4:
    check("c4 got adjusted_boundaries applied", c4["start_sec"] == 90.0 and c4["end_sec"] == 130.0,
          f"({c4['start_sec']}–{c4['end_sec']})")
    check("c4 marked _gate1_adjusted", c4.get("_gate1_adjusted") is True)

# Verify hook annotations land on the right candidates
c1 = next((c for c in accepted if c["clip_id"] == "c1"), None)
if c1:
    check("c1 has _gate1_engagement_risk=low", c1.get("_gate1_engagement_risk") == "low")

c6 = next((c for c in accepted if c["clip_id"] == "c6"), None)
if c6:
    check("c6 has _gate1_engagement_risk=medium", c6.get("_gate1_engagement_risk") == "medium")

# Verify QA log has 6 entries (one per candidate even rejected)
if log_path.exists():
    log_lines = log_path.read_text().strip().split("\n")
    check("qa_log has 6 entries", len(log_lines) == 6, f"({len(log_lines)})")

# Cleanup
if log_path.exists(): log_path.unlink()

print(f"\nResult: {ok} passed, {fail} failed")
sys.exit(0 if fail == 0 else 1)
