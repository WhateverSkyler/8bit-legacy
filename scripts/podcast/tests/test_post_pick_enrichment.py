#!/usr/bin/env python3
"""Verify post-pick enrichment + new hashtag merging behavior."""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

P = Path("/Users/tristanaddi1/Projects/8bit-legacy")
load_dotenv(P / "config" / ".env")
sys.path.insert(0, str(P / "scripts" / "podcast"))
sys.path.insert(0, str(P / "scripts"))

from _caption import merged_hashtags, BASELINE_HASHTAGS, FALLBACK_HASHTAGS, MAX_TOTAL_HASHTAGS

ok = 0
fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: print(f"  PASS: {label} {detail}"); ok += 1
    else:    print(f"  FAIL: {label} {detail}"); fail += 1

# === Test 1: merged_hashtags with no llm_tags falls back to baseline + topic + fallback ===
print("\n=== merged_hashtags backwards-compat (no llm_tags) ===")
result = merged_hashtags(["Black Flag", "Ubisoft"])
print(f"  Result: {result}")
check("contains #fyp", "#fyp" in result)
check("contains #8bitlegacy", "#8bitlegacy" in result)
check("contains topic-derived", "#blackflag" in result)
check("contains fallback #retrogaming", "#retrogaming" in result)
check("at most 15 tags", len(result.split()) <= 15)

# === Test 2: merged_hashtags WITH llm_tags prioritizes them ===
print("\n=== merged_hashtags with LLM tags ===")
llm = ["#assassinscreed", "#piratevideogames", "#openworld", "#ubisoftnews"]
result = merged_hashtags(["Black Flag"], llm)
print(f"  Result: {result}")
check("contains #fyp (baseline)", "#fyp" in result)
check("contains #8bitlegacy (brand)", "#8bitlegacy" in result)
check("contains LLM tag #assassinscreed", "#assassinscreed" in result)
check("contains LLM tag #piratevideogames", "#piratevideogames" in result)
check("at most 15 tags", len(result.split()) <= 15)

# === Test 3: Mock Claude to test _post_pick_enrichment routing ===
print("\n=== _post_pick_enrichment (mocked Claude) ===")
import _qa_helpers
mock_log: list[str] = []
async def _mock_text(prompt, model=None, max_tokens=None, retry_hint=None):
    await asyncio.sleep(0.01)
    if "audit the title" in prompt.lower():
        # Title quality
        if "vague generic" in prompt.lower():
            return {"decision": "REWRITE", "rewritten_title": "GameStop's eBay Disaster Costs Sellers Thousands",
                    "scores": {"specific":"fail","not_clickbait":"good","length":"good","accurate":"good"},
                    "reason": "vague→specific", "issues": ["vague"],
                    "_meta": {"model":"claude-sonnet-4-6","tokens_in":300,"tokens_out":50,"latency_ms":1}}
        return {"decision": "APPROVE", "scores": {"specific":"good","not_clickbait":"good","length":"good","accurate":"good"},
                "rewritten_title": None, "issues": [], "reason": "fine",
                "_meta": {"model":"claude-sonnet-4-6","tokens_in":300,"tokens_out":50,"latency_ms":1}}
    if "hashtags" in prompt.lower() and "generate platform-optimized" in prompt.lower():
        return {"hashtags": ["#assassinscreed", "#piratevideogames", "#openworld", "#blackflag", "#ubisoft"],
                "reason": "specific to clip",
                "_meta": {"model":"claude-sonnet-4-6","tokens_in":300,"tokens_out":50,"latency_ms":1}}
    if "categorize the clip's emotional energy" in prompt.lower():
        return {"mood": "intense", "music_volume": 0.08, "reason": "heated",
                "_meta": {"model":"claude-sonnet-4-6","tokens_in":300,"tokens_out":50,"latency_ms":1}}
    return {"decision": "APPROVE", "_meta": {"model":"x","tokens_in":1,"tokens_out":1,"latency_ms":1}}

_qa_helpers.call_claude_text_async = _mock_text

from pick_clips import _post_pick_enrichment

picks = [
    {"clip_id": "c1", "title": "Black Flag Pricing Debate", "hook": "?",
     "topics": ["Black Flag"], "source_stem": "test_episode",
     "start_sec": 0, "end_sec": 60},
    {"clip_id": "c2", "title": "vague generic title", "hook": "?",
     "topics": ["test"], "source_stem": "test_episode",
     "start_sec": 60, "end_sec": 120},
]

# Build a transcript with enough text per range
transcript = {"segments": [
    {"start": 0, "end": 60, "text": "This is detailed content about Black Flag and Assassins Creed pricing. " * 10},
    {"start": 60, "end": 120, "text": "More detailed content about a different topic with substance. " * 10},
]}

# Reset log file
log_path = P / "data" / "podcast" / "qa_logs" / "test_episode.jsonl"
if log_path.exists(): log_path.unlink()

enriched = _post_pick_enrichment(picks, transcript)
print()
check("2 picks returned", len(enriched) == 2)

c1 = next((p for p in enriched if p["clip_id"] == "c1"), None)
c2 = next((p for p in enriched if p["clip_id"] == "c2"), None)

if c1:
    check("c1 retains original title (APPROVE)", c1["title"] == "Black Flag Pricing Debate")
    check("c1 got LLM hashtags", "_llm_hashtags" in c1)
    check("c1 hashtags include #assassinscreed", "#assassinscreed" in (c1.get("_llm_hashtags") or []))
    check("c1 audio_mood=intense", c1.get("_audio_mood") == "intense")
    check("c1 music_volume=0.08", c1.get("_audio_music_volume") == 0.08)

if c2:
    check("c2 title was REWRITTEN", c2["title"] == "GameStop's eBay Disaster Costs Sellers Thousands")
    check("c2 _title_rewritten=True", c2.get("_title_rewritten") is True)
    check("c2 _original_title preserved", c2.get("_original_title") == "vague generic title")

# Verify log entries
if log_path.exists():
    lines = log_path.read_text().strip().split("\n")
    # 2 picks × 3 audits = 6 log entries
    check("6 log entries written (2 clips × 3 audits)", len(lines) == 6, f"({len(lines)})")
    log_path.unlink()

print(f"\nResult: {ok} passed, {fail} failed")
sys.exit(0 if fail == 0 else 1)
