#!/usr/bin/env python3
"""Summarize a per-episode QA gate-decision log.

Reads data/podcast/qa_logs/<episode>.jsonl (written by log_gate_decision in
_qa_helpers.py) and prints:
  - decisions per gate (PASS / REJECT / FLAG / ADJUST)
  - tokens + cost per gate
  - clips that were rejected and why (one-line summary each)
  - clips that needed rerender rescue (Gate 2 offset, Gate 3 stricter scenes)
  - total $ spent on the episode

Use cases:
  - After a pipeline run: confirm cost stayed under expected band
  - When a clip is unexpectedly missing: trace which gate dropped it
  - When tuning prompts: see which gates are most frequently hit

Usage:
  python3 scripts/podcast/qa_log_summary.py                       # all episodes
  python3 scripts/podcast/qa_log_summary.py <episode_stem>        # one episode
  python3 scripts/podcast/qa_log_summary.py --reasons <stem>      # also print reasons
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
QA_LOG_DIR = ROOT / "data" / "podcast" / "qa_logs"


def _load_log(jsonl_path: Path) -> list[dict]:
    """Read a JSONL file. Tolerates partial/corrupt lines."""
    records: list[dict] = []
    if not jsonl_path.exists():
        return records
    for line in jsonl_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _decision_for(rec: dict) -> str:
    """Extract the canonical decision string from a verdict."""
    v = rec.get("verdict", {}) or {}
    # Try fields that different gates use
    for field in ("decision", "recommendation", "final_decision"):
        val = v.get(field)
        if val:
            return str(val).upper()
    return "?"


def _summarize(records: list[dict], stem: str, with_reasons: bool = False) -> None:
    """Print summary for one episode."""
    if not records:
        print(f"  (no records for {stem})")
        return

    total_tokens_in = 0
    total_tokens_out = 0
    total_cost = 0.0
    total_latency_ms = 0

    by_gate: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_gate[rec.get("gate", "?")].append(rec)
        total_tokens_in += rec.get("tokens_in", 0) or 0
        total_tokens_out += rec.get("tokens_out", 0) or 0
        total_cost += rec.get("cost_usd", 0.0) or 0.0
        total_latency_ms += rec.get("latency_ms", 0) or 0

    print(f"\n=== Episode: {stem} ===")
    print(f"  total decisions: {len(records)}")
    print(f"  total tokens:    {total_tokens_in:,} in + {total_tokens_out:,} out")
    print(f"  total cost:      ${total_cost:.4f}")
    print(f"  total latency:   {total_latency_ms/1000:.1f}s "
          f"(avg {total_latency_ms / max(1, len(records)) / 1000:.1f}s per call)")

    print(f"\n  Per-gate breakdown:")
    print(f"  {'gate':<14} {'n':>4} {'tokens_in':>12} {'tokens_out':>12} "
          f"{'$cost':>10} {'avg_ms':>8}")
    print(f"  {'-'*14} {'-'*4:>4} {'-'*12:>12} {'-'*12:>12} {'-'*10:>10} {'-'*8:>8}")
    for gate in sorted(by_gate):
        recs = by_gate[gate]
        gtin = sum(r.get("tokens_in", 0) for r in recs)
        gtout = sum(r.get("tokens_out", 0) for r in recs)
        gcost = sum(r.get("cost_usd", 0) for r in recs)
        glat = sum(r.get("latency_ms", 0) for r in recs)
        avg_ms = glat / max(1, len(recs))
        print(f"  {gate:<14} {len(recs):>4} {gtin:>12,} {gtout:>12,} "
              f"${gcost:>9.4f} {avg_ms:>8.0f}")

    # Decision distribution per gate
    print(f"\n  Decisions per gate:")
    for gate in sorted(by_gate):
        decisions: dict[str, int] = defaultdict(int)
        for r in by_gate[gate]:
            decisions[_decision_for(r)] += 1
        chunks = ", ".join(f"{d}={n}" for d, n in sorted(decisions.items()))
        print(f"    {gate:<14}: {chunks}")

    # Rejects + flags — the actionable list
    rejects: list[dict] = []
    flags: list[dict] = []
    rescues: list[dict] = []
    for r in records:
        d = _decision_for(r)
        v = r.get("verdict", {}) or {}
        if d in ("REJECT", "REJECT_REFRAME"):
            rejects.append(r)
        elif d in ("FLAG_FOR_REVIEW", "MANUAL_REVIEW"):
            flags.append(r)
        if v.get("_rescued_from_offset") is not None or v.get("_rescued_from"):
            rescues.append(r)

    if rejects:
        print(f"\n  Rejects ({len(rejects)}):")
        for r in rejects:
            v = r.get("verdict", {}) or {}
            reason = (v.get("reason") or "?")[:120]
            print(f"    [{r.get('gate', '?')}] {r.get('clip_id', '?')[:50]} — {reason}")
            if with_reasons:
                issues = v.get("issues") or []
                for iss in issues[:5]:
                    if isinstance(iss, dict):
                        print(f"        - [{iss.get('severity','?')}] {iss.get('issue','?')[:120]}")
                    else:
                        print(f"        - {str(iss)[:120]}")

    if flags:
        print(f"\n  Flags for review ({len(flags)}):")
        for r in flags:
            v = r.get("verdict", {}) or {}
            reason = (v.get("reason") or "?")[:120]
            print(f"    [{r.get('gate', '?')}] {r.get('clip_id', '?')[:50]} — {reason}")

    if rescues:
        print(f"\n  Rescues that succeeded ({len(rescues)}):")
        for r in rescues:
            v = r.get("verdict", {}) or {}
            kind = (f"caption-offset {v.get('_rescued_from_offset')}s"
                    if v.get('_rescued_from_offset') is not None
                    else f"reframe ({v.get('_new_scene_count', '?')} new scenes)")
            print(f"    [{r.get('gate', '?')}] {r.get('clip_id', '?')[:50]} — {kind}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a per-episode QA log")
    parser.add_argument("episode_stem", nargs="?",
                        help="Episode stem (omit for all). Matches data/podcast/qa_logs/<stem>.jsonl")
    parser.add_argument("--reasons", action="store_true",
                        help="Print issue lists for rejected clips")
    args = parser.parse_args()

    if not QA_LOG_DIR.exists():
        print(f"No qa_logs dir at {QA_LOG_DIR}")
        return 0

    if args.episode_stem:
        path = QA_LOG_DIR / f"{args.episode_stem}.jsonl"
        if not path.exists():
            print(f"Log not found: {path}")
            return 2
        _summarize(_load_log(path), args.episode_stem, with_reasons=args.reasons)
    else:
        for jsonl in sorted(QA_LOG_DIR.glob("*.jsonl")):
            _summarize(_load_log(jsonl), jsonl.stem, with_reasons=args.reasons)
    return 0


if __name__ == "__main__":
    sys.exit(main())
