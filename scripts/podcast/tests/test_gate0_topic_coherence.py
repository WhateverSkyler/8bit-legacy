#!/usr/bin/env python3
"""Verify Gate 0 (topic coherence) routing: PASS keeps, SPLIT drops, INCOHERENT drops.

Mocks call_claude_text_async with canned verdicts to exercise all 3 decision paths.
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

P = Path("/Users/tristanaddi1/Projects/8bit-legacy")
load_dotenv(P / "config" / ".env")
sys.path.insert(0, str(P / "scripts" / "podcast"))
sys.path.insert(0, str(P / "scripts"))

# Mock async Claude
import _qa_helpers
verdicts_queue = []
calls = []

async def _mock_async_text(prompt, model=None, max_tokens=None, retry_hint=None):
    if not verdicts_queue:
        raise RuntimeError("Mock exhausted")
    calls.append(1)
    await asyncio.sleep(0.05)
    v = verdicts_queue.pop(0)
    return {**v, "_meta": {"model": "claude-sonnet-4-6", "tokens_in": 200, "tokens_out": 50, "latency_ms": 50}}

_qa_helpers.call_claude_text_async = _mock_async_text

# Stub navi (Gate 0 uses emit_failure_navi_task from topic_segment, which uses requests)
import requests
_real_post = requests.post
def _fake_post(*a, **kw):
    class R:
        status_code = 200
        def json(self): return {"id": -1}
        def raise_for_status(self): pass
    return R()
requests.post = _fake_post

from topic_segment import _gate0_topic_coherence

# 4 fake topics with various coherence states
topics = [
    {"slug": "good-topic", "title_hint": "Why Adults Quit Gaming", "thesis": "...",
     "start_sec": 0, "end_sec": 300, "duration_sec": 300},
    {"slug": "split-topic", "title_hint": "Black Flag pricing", "thesis": "...",
     "start_sec": 300, "end_sec": 600, "duration_sec": 300},
    {"slug": "incoherent", "title_hint": "Random rambling", "thesis": "...",
     "start_sec": 600, "end_sec": 900, "duration_sec": 300},
    {"slug": "another-good", "title_hint": "Switch 2 hype", "thesis": "...",
     "start_sec": 900, "end_sec": 1200, "duration_sec": 300},
]

# Build a transcript with text covering each topic's range
segments = [
    {"start": float(i*300), "end": float((i+1)*300),
     "text": f"This is topic {i+1} content. It contains plenty of words to satisfy the 200-character minimum that Gate 0 requires before it will actually run a coherence check. Real text would be much longer than this synthetic stub but this should suffice."}
    for i in range(4)
]

verdicts_queue.extend([
    {"decision": "PASS", "primary_subject": "x", "title_match": "good", "thesis_holds": True, "reason": "good"},
    {"decision": "SPLIT", "primary_subject": "Black Flag", "secondary_subjects": ["Resident Evil"],
     "split_timestamp_sec": 450.0, "title_match": "vague", "thesis_holds": False, "reason": "splits"},
    {"decision": "INCOHERENT", "primary_subject": "?", "title_match": "wrong",
     "thesis_holds": False, "reason": "rambles"},
    {"decision": "PASS", "primary_subject": "x", "title_match": "good", "thesis_holds": True, "reason": "good"},
])

# Reset log
log_path = P / "data" / "podcast" / "qa_logs" / "gate0_test_episode.jsonl"
if log_path.exists(): log_path.unlink()

print(f"Running Gate 0 against {len(topics)} fake topics with mocked verdicts...")
kept = _gate0_topic_coherence(topics, segments, "gate0_test_episode")

ok = 0
fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: print(f"  PASS: {label} {detail}"); ok += 1
    else:    print(f"  FAIL: {label} {detail}"); fail += 1

check("4 mock calls fired", len(calls) == 4, f"({len(calls)})")
check("PASS topic kept", any(t["slug"] == "good-topic" for t in kept))
check("SPLIT topic dropped", not any(t["slug"] == "split-topic" for t in kept))
check("INCOHERENT topic dropped", not any(t["slug"] == "incoherent" for t in kept))
check("Second PASS topic kept", any(t["slug"] == "another-good" for t in kept))
check("Total kept = 2", len(kept) == 2, f"({len(kept)})")

# Verify QA log
if log_path.exists():
    lines = log_path.read_text().strip().split("\n")
    check("4 log entries (one per topic)", len(lines) == 4, f"({len(lines)})")

# Cleanup
if log_path.exists(): log_path.unlink()
requests.post = _real_post

print(f"\nGate 0 routing: {ok} passed, {fail} failed")
sys.exit(0 if fail == 0 else 1)
