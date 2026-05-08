#!/usr/bin/env python3
"""Phase 1C v2 — verify reject-path PLUMBING directly.

The previous test relied on Claude actually rejecting. Better: test the routing
logic itself — move_to_rejected() + emit_reject_navi() — with a synthetic verdict.
This proves the plumbing works regardless of whether the LLM happens to reject.
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

# Stub Navi BEFORE importing _qa_helpers so the module-level import sees the stub
import navi_alerts
emit_calls = []
def _stub_emit(title, description, priority="medium", source="8bit"):
    emit_calls.append({"title": title, "priority": priority,
                       "description": description[:300]})
    return -1
navi_alerts.emit_navi_task = _stub_emit

# Re-bind the symbol _qa_helpers imported at module load time
import _qa_helpers
_qa_helpers.emit_navi_task = _stub_emit

from _qa_helpers import (
    move_to_rejected, emit_reject_navi, emit_flag_navi, log_gate_decision,
)

# Sandbox
tmp = Path(tempfile.mkdtemp(prefix="qa-reject-plumbing-"))
sandbox_episode = tmp / "Test_Episode"
sandbox_episode.mkdir(parents=True, exist_ok=True)

# Fake clip
fake_clip = sandbox_episode / "test_c2.mp4"
fake_clip.write_bytes(b"fake mp4 contents for plumbing test")
print(f"Sandbox: {tmp}")
print(f"Fake clip: {fake_clip} (bytes={fake_clip.stat().st_size})")

# Fabricate a "Claude said reject" verdict
synthetic_verdict = {
    "recommendation": "reject",
    "sync_quality": "misaligned",
    "issues": ["captions visibly out of sync with lip movement in both keyframes"],
    "reason": "Synthetic test verdict — captions misaligned",
    "_meta": {
        "model": "claude-sonnet-4-6",
        "tokens_in": 1234,
        "tokens_out": 89,
        "latency_ms": 4321,
    },
}

# === TEST 1: move_to_rejected ===
print()
print("=" * 60)
print("TEST 1: move_to_rejected()")
print("=" * 60)
target = move_to_rejected(fake_clip, sandbox_episode, "Gate 2 (test)",
                           synthetic_verdict, "test_c2")

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

rejected_dir = sandbox_episode / "_rejected"
check("_rejected/ created", rejected_dir.is_dir())
moved = rejected_dir / "test_c2.mp4"
check("clip moved into _rejected/", moved.exists())
check("original gone", not fake_clip.exists())
reason_file = rejected_dir / "test_c2_reject.json"
check("reason JSON written", reason_file.exists())
if reason_file.exists():
    body = json.loads(reason_file.read_text())
    check("reason has 'gate' key", "gate" in body)
    check("reason has 'reason' key", "reason" in body)
    check("reason captures verdict", body["reason"].get("recommendation") == "reject")
    print(f"    Body: {json.dumps(body, indent=2)[:400]}")

# === TEST 2: emit_reject_navi ===
print()
print("=" * 60)
print("TEST 2: emit_reject_navi()")
print("=" * 60)
emit_reject_navi("test_c2", "Gate 2 (test)", synthetic_verdict, "test_episode")
check("Navi emit was called", len(emit_calls) >= 1)
if emit_calls:
    c = emit_calls[-1]
    check("priority=high", c["priority"] == "high")
    check("title contains clip_id", "test_c2" in c["title"])
    check("title contains gate", "Gate 2" in c["title"])
    print(f"    Title: {c['title']}")
    print(f"    Description preview: {c['description'][:200]}")

# === TEST 3: emit_flag_navi ===
print()
print("=" * 60)
print("TEST 3: emit_flag_navi()")
print("=" * 60)
emit_calls.clear()
emit_flag_navi("test_c3", "Gate 3 (framing)",
               [{"severity": "minor", "issue": "frame at 75% slightly left"}],
               "test_episode")
check("Navi emit was called", len(emit_calls) == 1)
if emit_calls:
    c = emit_calls[-1]
    check("priority=medium for FLAG", c["priority"] == "medium")
    check("title says 'review'", "review" in c["title"].lower() or "QA review" in c["title"])

# === TEST 4: log_gate_decision ===
print()
print("=" * 60)
print("TEST 4: log_gate_decision()")
print("=" * 60)
log_gate_decision("plumbing_test_episode", "gate2_test", "test_c2",
                  synthetic_verdict, extra={"duration_sec": 30.0})
log_path = P / "data" / "podcast" / "qa_logs" / "plumbing_test_episode.jsonl"
check("qa_logs file created", log_path.exists())
if log_path.exists():
    last_line = log_path.read_text().strip().split("\n")[-1]
    record = json.loads(last_line)
    check("log has tokens_in", record.get("tokens_in") == 1234)
    check("log has tokens_out", record.get("tokens_out") == 89)
    check("log has cost_usd", record.get("cost_usd", 0) > 0)
    check("log preserves verdict", record["verdict"]["recommendation"] == "reject")
    check("log strips _meta from verdict", "_meta" not in record["verdict"])
    check("extra is merged", record.get("duration_sec") == 30.0)
    print(f"    Log entry: {json.dumps(record, indent=2)[:500]}")

# Summary
print()
print("=" * 60)
print(f"TOTAL: {ok} passed, {fail} failed")
print("=" * 60)

# Clean up the test JSONL we wrote so we don't leave artifacts in real qa_logs
if log_path.exists():
    log_path.unlink()
    print(f"Cleaned up test log: {log_path}")

sys.exit(0 if fail == 0 else 1)
