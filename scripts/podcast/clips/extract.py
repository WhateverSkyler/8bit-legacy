"""CLI orchestrator: extract short-form clips from podcast transcripts.

Replaces the legacy `pick_clips.py` entrypoint. Accepts the same invocation
patterns that `pipeline.py` and `deploy/test-on-episode.sh` already use, so
the wiring stays clean.

For each transcript: pre-process (silence + anchored transcript + topic
context) → ONE Sonnet call (forced tool-use) → structural verification
→ write per-topic JSON. After all transcripts: rebuild _all.json.

All transcripts run in parallel via asyncio.gather().

Flags accepted-but-ignored from the legacy CLI:
  --target-count N    (quantity is now model-driven, no cap)
  --chunk-minutes N   (no chunking — one call per topic file)

These are kept silent-with-warning so existing callers don't break.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import traceback
from pathlib import Path

# Allow `python3 scripts/podcast/clips/extract.py ...` without a package install
_THIS_DIR = Path(__file__).resolve().parent
_PARENT_OF_PACKAGE = _THIS_DIR.parent.parent
if str(_PARENT_OF_PACKAGE) not in sys.path:
    sys.path.insert(0, str(_PARENT_OF_PACKAGE))

from podcast.clips.silence_breakpoints import (  # noqa: E402
    Breakpoint, compute_breakpoints, find_breakpoint_for_audio,
)
from podcast.clips.anchored_transcript import (  # noqa: E402
    build_anchored_transcript, build_breakpoint_table, estimate_input_tokens,
)
from podcast.clips.topic_context import load_topic_context, TopicContext  # noqa: E402
from podcast.clips.editorial_call import (  # noqa: E402
    SONNET_MODEL, OPUS_MODEL, call_editorial_async, EditorialResult, estimate_cost,
)
from podcast.clips.verify import verify, VerifyOutput  # noqa: E402
from podcast.clips.spec_writer import write_topic_plan, rebuild_all_json  # noqa: E402


def _resolve_model(name: str) -> str:
    name = (name or "").lower().strip()
    if name in ("opus", OPUS_MODEL):
        return OPUS_MODEL
    return SONNET_MODEL


def _gather_transcript_paths(args) -> list[Path]:
    """Resolve CLI args to a concrete list of transcript JSON files."""
    paths: list[Path] = []
    for p in args.transcripts:
        path = Path(p)
        if path.is_file():
            paths.append(path)
        else:
            print(f"[skip] not a file: {path}")

    if args.batch:
        batch_dir = Path(args.batch)
        if not batch_dir.exists():
            print(f"[fatal] --batch dir missing: {batch_dir}")
            return []
        paths.extend(sorted(batch_dir.glob("*.json")))

    # Filter by mtime if requested
    if args.mtime_within_days is not None:
        cutoff = time.time() - (args.mtime_within_days * 86400)
        before = len(paths)
        paths = [p for p in paths if p.stat().st_mtime >= cutoff]
        skipped = before - len(paths)
        if skipped:
            print(f"  [mtime] skipped {skipped} transcripts older than {args.mtime_within_days} days")

    # Drop dotfiles, dedupe while preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        if p.name.startswith(".") or p.name.startswith("_"):
            continue
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _preprocess(transcript_path: Path,
                episode_dir: Path | None,
                use_cache: bool = True) -> tuple[dict, list[Breakpoint], TopicContext, str, str]:
    """Build all the inputs needed for the editorial call. Pure I/O + computation."""
    transcript = json.loads(transcript_path.read_text())
    audio_path = find_breakpoint_for_audio(transcript_path)
    topic_ctx = load_topic_context(transcript_path, transcript, episode_dir=episode_dir)
    breakpoints = compute_breakpoints(audio_path, topic_ctx.duration_sec, use_cache=use_cache)
    anchored = build_anchored_transcript(transcript, breakpoints)
    bp_table = build_breakpoint_table(breakpoints)
    return transcript, breakpoints, topic_ctx, anchored, bp_table


async def _extract_one(transcript_path: Path,
                       episode_dir: Path | None,
                       model: str,
                       prompt_version: str,
                       dry_run: bool,
                       use_cache: bool) -> dict:
    """Process one transcript end-to-end. Returns a per-topic summary dict."""
    stem = transcript_path.stem
    summary = {
        "transcript": str(transcript_path),
        "source_stem": stem,
        "ok": False,
        "error": "",
        "n_breakpoints": 0,
        "n_picks_returned": 0,
        "n_specs_kept": 0,
        "n_specs_dropped": 0,
        "no_clips_reason": "",
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "latency_sec": 0.0,
    }

    try:
        transcript, breakpoints, topic_ctx, anchored, bp_table = _preprocess(
            transcript_path, episode_dir, use_cache=use_cache,
        )
    except Exception as exc:
        summary["error"] = f"preprocess_failed: {exc}"
        traceback.print_exc()
        return summary

    summary["n_breakpoints"] = len(breakpoints)
    if not breakpoints:
        summary["error"] = "no_breakpoints (topic too quiet, too short, or audio missing)"
        # Still write an empty plan so downstream knows we processed it.
        write_topic_plan(stem, [])
        summary["ok"] = True
        return summary

    if dry_run:
        est_tokens = estimate_input_tokens(anchored, bp_table)
        est_cost = estimate_cost(est_tokens, 600, model=model)
        print(
            f"  [dry-run] {stem}: {len(breakpoints)} breakpoints, ~{est_tokens} input tokens, "
            f"~${est_cost:.3f} estimated cost (model={model})"
        )
        summary["tokens_in"] = est_tokens
        summary["cost_usd"] = est_cost
        summary["ok"] = True
        return summary

    topic_block = topic_ctx.render_for_prompt()
    try:
        result: EditorialResult = await call_editorial_async(
            topic_block, anchored, bp_table,
            model=model, prompt_version=prompt_version,
        )
    except Exception as exc:
        summary["error"] = f"editorial_call_failed: {exc}"
        traceback.print_exc()
        return summary

    summary["n_picks_returned"] = len(result.picks)
    summary["no_clips_reason"] = result.no_clips_reason
    summary["tokens_in"] = result.tokens_in
    summary["tokens_out"] = result.tokens_out
    summary["cost_usd"] = result.cost_usd
    summary["latency_sec"] = result.latency_sec

    verified: VerifyOutput = verify(
        result.picks, breakpoints, topic_ctx, source_stem=stem,
        model=result.model, prompt_version=result.prompt_version,
    )
    summary["n_specs_kept"] = len(verified.specs)
    summary["n_specs_dropped"] = len(verified.dropped)

    write_topic_plan(stem, verified.specs)

    print(
        f"  [done] {stem}: {len(result.picks)} picks → {len(verified.specs)} kept "
        f"(dropped {len(verified.dropped)}); ${result.cost_usd:.3f}, {result.latency_sec:.1f}s"
    )
    if verified.dropped:
        for d in verified.dropped:
            print(f"    drop: \"{d.pick.title[:50]}\" → {d.reason}")
    if not result.picks and result.no_clips_reason:
        print(f"    no-clips reason: {result.no_clips_reason}")

    summary["ok"] = True
    return summary


async def _run_all(transcripts: list[Path],
                   episode_dir: Path | None,
                   model: str,
                   prompt_version: str,
                   dry_run: bool,
                   use_cache: bool) -> list[dict]:
    tasks = [
        _extract_one(t, episode_dir, model, prompt_version, dry_run, use_cache)
        for t in transcripts
    ]
    return await asyncio.gather(*tasks, return_exceptions=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract short-form clip specs from podcast transcripts.",
    )
    parser.add_argument("transcripts", nargs="*", type=str,
                        help="One or more transcript JSON file paths.")
    parser.add_argument("--batch", type=str, default=None,
                        help="Directory of transcripts to process (in addition to positional args).")
    parser.add_argument("--episode-dir", type=str, default=None,
                        help="Path to data/podcast/<EpisodeDir>/ for auto_segment_plan lookup. "
                             "Auto-discovered if omitted.")
    parser.add_argument("--mtime-within-days", type=int, default=None,
                        help="Skip transcripts older than this many days.")
    parser.add_argument("--model", type=str, default="sonnet",
                        help="sonnet (default) | opus")
    parser.add_argument("--prompt-version", type=str, default="v1",
                        help="Which prompts/system_v*.md to use (default v1).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Pre-process only; estimate tokens/cost; do not call API.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Force ffmpeg silencedetect to re-run instead of using cached breakpoints.")
    # Legacy flags accepted-but-ignored
    parser.add_argument("--target-count", type=int, default=None,
                        help="(IGNORED) Quantity is model-driven; this flag has no effect.")
    parser.add_argument("--chunk-minutes", type=int, default=None,
                        help="(IGNORED) Pipeline now operates per-topic-file; this flag has no effect.")

    args = parser.parse_args()

    # Loud warnings for ignored flags
    if args.target_count is not None:
        print(f"  [warn] --target-count={args.target_count} is IGNORED. "
              f"Quantity is model-driven (zero is a valid count).")
    if args.chunk_minutes is not None:
        print(f"  [warn] --chunk-minutes={args.chunk_minutes} is IGNORED. "
              f"Pipeline operates one call per topic file.")

    transcripts = _gather_transcript_paths(args)
    if not transcripts:
        print("[fatal] no transcripts to process")
        return 2

    print(f"[extract] {len(transcripts)} transcript(s) to process "
          f"(model={_resolve_model(args.model)}, prompt={args.prompt_version}, "
          f"dry_run={args.dry_run})")

    episode_dir = Path(args.episode_dir) if args.episode_dir else None
    model = _resolve_model(args.model)

    t0 = time.time()
    summaries = asyncio.run(_run_all(
        transcripts, episode_dir, model, args.prompt_version, args.dry_run,
        use_cache=not args.no_cache,
    ))
    wall = time.time() - t0

    if not args.dry_run:
        all_path = rebuild_all_json()
        print(f"[extract] rebuilt {all_path}")

    total_cost = sum(s["cost_usd"] for s in summaries)
    total_kept = sum(s["n_specs_kept"] for s in summaries)
    total_dropped = sum(s["n_specs_dropped"] for s in summaries)
    n_failed = sum(1 for s in summaries if not s["ok"])
    print(
        f"[extract] done in {wall:.1f}s | "
        f"{total_kept} clips kept | {total_dropped} dropped | "
        f"${total_cost:.3f} total | {n_failed} failures"
    )
    if n_failed:
        print("[extract] failures:")
        for s in summaries:
            if not s["ok"]:
                print(f"  {s['transcript']}: {s['error']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
