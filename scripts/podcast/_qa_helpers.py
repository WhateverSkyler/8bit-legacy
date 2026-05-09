"""Quality-assurance helpers for the shorts pipeline.

Used by pick_clips.py (Gate 1), render_clip.py (Gate 2 + 3), and schedule_shorts.py (Gate 4)
to validate clips at each stage with Claude. The user's directive is "level of knowledge
equivalent to a team of humans" — these helpers wrap each LLM call with consistent error
handling, retry on JSON-decode failure, base64 encoding for vision, and reject-folder routing.

Design notes:
- All LLM calls use claude-sonnet-4-6 by default. Gate 4 uses claude-opus-4-7 for highest fidelity.
- Vision payload format: list of {"type":"image","source":{"type":"base64",...}} items + final text item.
- Reject path: every gate that decides REJECT calls move_to_rejected() with a reason file.
- Navi alerts: emitted on REJECT (priority=high) + FLAG_FOR_REVIEW (priority=medium).
- Prompts live in qa_prompts.py — versioned independently so we can iterate wording.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
try:
    from navi_alerts import emit_navi_task
except ImportError:
    emit_navi_task = None


SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-7"

# 2026-12 Anthropic published per-token pricing (USD per million tokens).
# Used for the per-episode cost estimate. Update if pricing changes.
MODEL_PRICING = {
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
    "claude-opus-4-7":   {"in": 15.00, "out": 75.00},
}

QA_LOG_DIR = ROOT / "data" / "podcast" / "qa_logs"


# ===== Anthropic client =====================================================

def _client():
    """Return an Anthropic client. Lazy import so the module loads without anthropic."""
    import anthropic
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ===== JSON parsing with fence-stripping ====================================

def parse_json_response(text: str) -> dict:
    """Strip markdown fences if Claude wrapped the JSON, then parse."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


# ===== Text-only Claude call (Gate 1) ========================================

def _meta_dict(resp, model: str, t_start: float) -> dict:
    """Build the _meta sub-dict attached to every verdict (cost + perf telemetry)."""
    usage = getattr(resp, "usage", None)
    tin = getattr(usage, "input_tokens", 0) if usage else 0
    tout = getattr(usage, "output_tokens", 0) if usage else 0
    return {
        "model": model,
        "tokens_in": tin,
        "tokens_out": tout,
        "latency_ms": int((time.time() - t_start) * 1000),
    }


def call_claude_text(prompt: str, model: str = SONNET_MODEL,
                    max_tokens: int = 1500, retry_hint: str = "") -> dict:
    """Single-turn text call returning parsed JSON. One retry on JSON decode error.

    Attaches a `_meta` key to the parsed verdict containing model, tokens_in,
    tokens_out, latency_ms — used by log_gate_decision for cost tracking."""
    full_prompt = (retry_hint + "\n\n" + prompt) if retry_hint else prompt
    t_start = time.time()
    resp = _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": full_prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    try:
        verdict = parse_json_response(text)
    except json.JSONDecodeError:
        # Single retry with reinforcement
        resp2 = _client().messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": "Return STRICT JSON only. No prose. No markdown fences. "
                          "Start with { end with }.\n\n" + full_prompt,
            }],
        )
        text2 = "".join(b.text for b in resp2.content if b.type == "text").strip()
        verdict = parse_json_response(text2)
        # Sum usage across both calls so cost reflects retry overhead
        m = _meta_dict(resp, model, t_start)
        m2 = _meta_dict(resp2, model, t_start)
        m["tokens_in"] += m2["tokens_in"]
        m["tokens_out"] += m2["tokens_out"]
        m["latency_ms"] = m2["latency_ms"]  # full elapsed including retry
        m["json_retries"] = 1
        verdict["_meta"] = m
        return verdict
    verdict["_meta"] = _meta_dict(resp, model, t_start)
    return verdict


# ===== Multimodal Claude call (Gates 2, 3, 4) ===============================

def encode_image_b64(path: Path) -> str:
    """Read an image file and return its base64 string for Claude vision API."""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def call_claude_vision(prompt: str, image_paths: list[Path],
                      model: str = SONNET_MODEL, max_tokens: int = 2000,
                      media_type: str = "image/jpeg") -> dict:
    """Multi-image vision call returning parsed JSON. One retry on JSON decode error.

    Attaches a `_meta` key to the verdict (model, tokens_in, tokens_out, latency_ms)."""
    content: list[dict] = []
    for img in image_paths:
        if not img.exists():
            continue
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encode_image_b64(img),
            },
        })
    content.append({"type": "text", "text": prompt})

    t_start = time.time()
    resp = _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    try:
        verdict = parse_json_response(text)
    except json.JSONDecodeError:
        # Reinforce + retry
        content[-1]["text"] = ("Return STRICT JSON only. No prose. No markdown fences. "
                                "Start with { end with }.\n\n" + content[-1]["text"])
        resp2 = _client().messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        text2 = "".join(b.text for b in resp2.content if b.type == "text").strip()
        verdict = parse_json_response(text2)
        m = _meta_dict(resp, model, t_start)
        m2 = _meta_dict(resp2, model, t_start)
        m["tokens_in"] += m2["tokens_in"]
        m["tokens_out"] += m2["tokens_out"]
        m["latency_ms"] = m2["latency_ms"]
        m["json_retries"] = 1
        verdict["_meta"] = m
        return verdict
    verdict["_meta"] = _meta_dict(resp, model, t_start)
    return verdict


# ===== Async wrappers (for concurrent gate execution) =======================
# Used by pick_clips.py Gate 1 to fire ~14 candidates' Claude text calls
# concurrently. Saves ~30-40s per episode by overlapping I/O-bound API calls.

async def call_claude_text_async(prompt: str, model: str = SONNET_MODEL,
                                 max_tokens: int = 1500, retry_hint: str = "") -> dict:
    """Async wrapper around call_claude_text — uses asyncio.to_thread so the
    sync Anthropic SDK runs on a worker thread without blocking the event loop.

    Concurrent use: kick off N calls via asyncio.gather() and they run in
    parallel up to the SDK's HTTP pool size (~100 by default).
    """
    import asyncio
    return await asyncio.to_thread(
        call_claude_text, prompt, model, max_tokens, retry_hint,
    )


async def call_claude_vision_async(prompt: str, image_paths: list,
                                   model: str = SONNET_MODEL,
                                   max_tokens: int = 2000,
                                   media_type: str = "image/jpeg") -> dict:
    """Async wrapper around call_claude_vision. Use for parallel Gate 4 across
    multiple clips, or Gate 2 + Gate 3 on the same clip."""
    import asyncio
    return await asyncio.to_thread(
        call_claude_vision, prompt, image_paths, model, max_tokens, media_type,
    )


# ===== Decision logging (per-episode JSONL) =================================

def log_gate_decision(episode_stem: str, gate: str, clip_id: str,
                      verdict: dict, extra: dict | None = None) -> None:
    """Append one line to data/podcast/qa_logs/<episode_stem>.jsonl.

    Reads `verdict["_meta"]` if present (set by call_claude_*) and computes a
    cost estimate from MODEL_PRICING. Use for retrospective analysis,
    prompt-tuning, and per-episode cost tracking.

    Caller should pass the FULL verdict dict from the gate — the log keeps
    the LLM's decision + reasoning verbatim for post-mortem analysis.
    """
    QA_LOG_DIR.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", episode_stem) or "unknown"
    log_path = QA_LOG_DIR / f"{safe_stem}.jsonl"

    meta = (verdict or {}).get("_meta", {}) or {}
    model = meta.get("model", "?")
    tin = meta.get("tokens_in", 0)
    tout = meta.get("tokens_out", 0)
    pricing = MODEL_PRICING.get(model, {"in": 0, "out": 0})
    cost_usd = (tin / 1_000_000) * pricing["in"] + (tout / 1_000_000) * pricing["out"]

    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z") or time.strftime("%Y-%m-%dT%H:%M:%S"),
        "episode": episode_stem,
        "gate": gate,
        "clip_id": clip_id,
        "model": model,
        "tokens_in": tin,
        "tokens_out": tout,
        "latency_ms": meta.get("latency_ms", 0),
        "cost_usd": round(cost_usd, 6),
        "verdict": {k: v for k, v in (verdict or {}).items() if k != "_meta"},
    }
    if extra:
        record.update(extra)
    try:
        with log_path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        print(f"  [qa-log] write failed: {exc}")


# ===== Keyframe extraction (ffmpeg) ==========================================

def extract_keyframes(video: Path, timestamps_sec: list[float],
                     out_dir: Path, prefix: str = "kf") -> list[Path]:
    """Extract one JPEG per timestamp via ffmpeg `-ss N -frames:v 1`. Returns paths.

    Skipped if extraction fails for a given timestamp (logs warning, continues).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    for i, ts in enumerate(timestamps_sec):
        out = out_dir / f"{prefix}_{i:02d}_{ts:.2f}s.jpg"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{ts:.3f}",
            "-i", str(video),
            "-frames:v", "1",
            "-q:v", "3",  # high quality JPEG
            str(out),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            if out.exists() and out.stat().st_size > 0:
                out_paths.append(out)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"  [keyframe] failed t={ts}s: {exc}")
    return out_paths


def video_duration_sec(video: Path) -> float:
    """Return duration in seconds via ffprobe. Returns 0.0 on error."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(video)],
            check=True, capture_output=True, text=True, timeout=10,
        )
        return float(out.stdout.strip() or 0)
    except Exception:
        return 0.0


# ===== Reject / flag routing ================================================

def move_to_rejected(clip_path: Path, episode_dir: Path,
                     gate: str, reason: dict, clip_id: str | None = None) -> Path:
    """Move a rejected MP4 + write a JSON reason file alongside.

    rejected/<clip_id>/<clip_id>.mp4 + <clip_id>_reject.json
    """
    rejected_dir = episode_dir / "_rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    cid = clip_id or clip_path.stem
    target = rejected_dir / clip_path.name
    if clip_path.exists():
        try:
            shutil.move(str(clip_path), str(target))
        except Exception as exc:
            print(f"  [reject] move failed: {exc}")
            target = clip_path  # fallback: leave in place
    reason_file = rejected_dir / f"{cid}_reject.json"
    reason_file.write_text(json.dumps({"gate": gate, "reason": reason}, indent=2))
    return target


def _per_clip_navi_enabled() -> bool:
    """Per-clip Navi tasks default OFF (user feedback 2026-05-08: spam).
    Disk logs (qa_logs/<source>.jsonl + <episode>/_rejected/*reject.json) remain.
    Set QA_GATE_NAVI_ENABLED=1 to bring back per-clip pings."""
    return os.getenv("QA_GATE_NAVI_ENABLED", "0") in ("1", "true", "True", "yes")


def emit_reject_navi(clip_id: str, gate: str, reason: dict, episode: str = "") -> None:
    """Emit a Navi task explaining why a clip was rejected.

    Default OFF — per-clip rejects flooded Tristan's Navi during multi-clip
    pipeline runs. Disk record at <episode>/_rejected/<clip_id>_reject.json
    + qa_logs/<source>.jsonl is the audit trail. Use emit_episode_summary_navi
    for a single end-of-run roll-up instead.
    """
    if not _per_clip_navi_enabled():
        return
    if emit_navi_task is None:
        print(f"  [navi] unavailable; reject reason logged to disk only")
        return
    body = (
        f"Clip rejected at {gate}.\n\n"
        f"Episode: {episode}\nClip: {clip_id}\n\n"
        f"Reason:\n{json.dumps(reason, indent=2)}"
    )
    try:
        emit_navi_task(
            title=f"QA reject: {clip_id} ({gate})",
            description=body,
            priority="high",
        )
    except Exception as exc:
        print(f"  [navi] emit failed: {exc}")


def emit_flag_navi(clip_id: str, gate: str, issues: list, episode: str = "") -> None:
    """Emit a Navi task for clips that need human review (FLAG_FOR_REVIEW).
    Default OFF — see emit_reject_navi docstring."""
    if not _per_clip_navi_enabled():
        return
    if emit_navi_task is None:
        return
    body = (
        f"Clip flagged for human review at {gate}.\n\n"
        f"Episode: {episode}\nClip: {clip_id}\n\n"
        f"Issues:\n" + "\n".join(f"  - [{i.get('severity','?')}] {i.get('issue','?')}" for i in issues)
    )
    try:
        emit_navi_task(
            title=f"QA review: {clip_id} ({gate})",
            description=body,
            priority="medium",
        )
    except Exception as exc:
        print(f"  [navi] emit failed: {exc}")


def emit_episode_summary_navi(episode_stem: str, totals: dict) -> None:
    """One Navi task per episode, after schedule completes.
    Replaces the per-clip spam. `totals` is a dict like:
        {"approved": 12, "flagged_shipping": 3, "rejected": 27, "total": 42, "cost_usd": 3.10}
    """
    if emit_navi_task is None:
        return
    try:
        approved = totals.get("approved", 0)
        flagged = totals.get("flagged_shipping", 0) + totals.get("flagged", 0)
        rejected = totals.get("rejected", 0)
        cost = totals.get("cost_usd", 0)
        body = (
            f"Episode QA summary — {episode_stem}\n\n"
            f"Approved + shipped: {approved}\n"
            f"Flagged but shipped: {flagged}\n"
            f"Rejected: {rejected}\n"
            f"Total processed: {totals.get('total', approved + flagged + rejected)}\n"
            f"QA cost: ${cost:.4f}\n\n"
            f"Per-clip details: data/podcast/qa_logs/<source_stem>.jsonl\n"
            f"Rejected MP4s: data/podcast/clips/<episode>/_rejected/\n"
            f"Run: python3 scripts/podcast/qa_log_summary.py {episode_stem}"
        )
        emit_navi_task(
            title=f"QA episode summary: {episode_stem[:50]} ({approved}+{flagged} shipped, {rejected} rejected)",
            description=body,
            priority="medium" if rejected > approved else "low",
        )
    except Exception as exc:
        print(f"  [navi] episode summary emit failed: {exc}")
