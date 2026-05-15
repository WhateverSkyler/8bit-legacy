"""The single editorial Claude call per topic.

Forces tool-use of `submit_clip_picks` so the model returns a structured
list of picks (or an empty list with a reason). Indices, not floats —
mid-sentence cuts are structurally impossible because a non-breakpoint
position simply isn't representable in the schema.

Sonnet 4.6 default. Opus 4.7 override available via `--model opus` for
A/B comparisons; Sonnet handles the prompt cleanly in initial testing.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic

SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-7"

# USD per million tokens (per Anthropic 2026-Q1 pricing)
_PRICING = {
    SONNET_MODEL: {"in": 3.00, "out": 15.00},
    OPUS_MODEL:   {"in": 15.00, "out": 75.00},
}

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# The submit_clip_picks tool schema — model must call this with its picks.
SUBMIT_CLIP_PICKS_TOOL = {
    "name": "submit_clip_picks",
    "description": (
        "Submit your editorial picks for this topic file. Return zero or "
        "more clip picks. If you find no moments worth shipping, return an "
        "empty picks array with a one-sentence no_clips_reason."
    ),
    "input_schema": {
        "type": "object",
        "required": ["picks"],
        "properties": {
            "no_clips_reason": {
                "type": "string",
                "description": "Required only when picks is empty.",
            },
            "picks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "start_b", "end_b", "title", "hook_line",
                        "payoff_summary", "single_topic_confirmation",
                        "confidence", "mood",
                    ],
                    "properties": {
                        "start_b": {
                            "type": "integer", "minimum": 0,
                            "description": "Index of the breakpoint that the clip starts at (clip starts AFTER this silence ends).",
                        },
                        "end_b": {
                            "type": "integer", "minimum": 0,
                            "description": "Index of the breakpoint that the clip ends at (clip ends WHEN this silence begins). Must be > start_b.",
                        },
                        "title": {
                            "type": "string", "maxLength": 60,
                            "description": "Title burned into the video. Punchy, present tense, ≤60 chars.",
                        },
                        "hook_line": {
                            "type": "string",
                            "description": "One sentence describing the opening beat of the clip.",
                        },
                        "payoff_summary": {
                            "type": "string",
                            "description": "One sentence on what lands at the end.",
                        },
                        "single_topic_confirmation": {
                            "type": "string",
                            "description": "State the topic in your own words to confirm single-topic compliance.",
                        },
                        "confidence": {
                            "type": "number", "minimum": 0, "maximum": 1,
                            "description": "Honest 0-1 estimate of cold-viewer success probability.",
                        },
                        "mood": {
                            "type": "string",
                            "enum": ["hype", "chill", "reflective", "funny", "heated", "hopeful"],
                            "description": "Emotional energy — drives music selection.",
                        },
                    },
                },
            },
        },
    },
}


@dataclass(frozen=True)
class ClipPick:
    """One pick the model returned, before structural verification."""
    start_b: int
    end_b: int
    title: str
    hook_line: str
    payoff_summary: str
    single_topic_confirmation: str
    confidence: float
    mood: str


@dataclass(frozen=True)
class EditorialResult:
    picks: list[ClipPick]
    no_clips_reason: str
    model: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_sec: float


def _load_prompt(version: str, kind: str) -> str:
    """Load a versioned prompt file. kind ∈ {'system', 'user_template'}."""
    path = PROMPTS_DIR / f"{kind}_{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt missing: {path}")
    return path.read_text()


def _client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


def _extract_tool_input(response) -> dict:
    """Pull the submit_clip_picks tool input out of the response. Raises if missing."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_clip_picks":
            return block.input or {}
    # Defensive: dump what we got for debugging
    rendered = "\n".join(
        f"  block {i}: type={getattr(b,'type','?')} {getattr(b,'name','')}"
        for i, b in enumerate(response.content)
    )
    raise RuntimeError(f"Model did not call submit_clip_picks. Response blocks:\n{rendered}")


def call_editorial_sync(topic_context_block: str,
                        anchored_transcript: str,
                        breakpoint_table: str,
                        *,
                        model: str = SONNET_MODEL,
                        prompt_version: str = "v1",
                        max_tokens: int = 4000) -> EditorialResult:
    """Synchronous editorial call. Returns ClipPick[] (possibly empty) with metadata."""
    system_prompt = _load_prompt(prompt_version, "system")
    user_template = _load_prompt(prompt_version, "user_template")
    user_message = (user_template
                    .replace("{topic_context}", topic_context_block)
                    .replace("{anchored_transcript}", anchored_transcript)
                    .replace("{breakpoint_table}", breakpoint_table))

    client = _client()
    t0 = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        tools=[SUBMIT_CLIP_PICKS_TOOL],
        tool_choice={"type": "tool", "name": "submit_clip_picks"},
        messages=[{"role": "user", "content": user_message}],
    )
    latency = time.time() - t0

    raw = _extract_tool_input(response)
    picks = [
        ClipPick(
            start_b=int(p["start_b"]),
            end_b=int(p["end_b"]),
            title=str(p["title"]),
            hook_line=str(p["hook_line"]),
            payoff_summary=str(p["payoff_summary"]),
            single_topic_confirmation=str(p["single_topic_confirmation"]),
            confidence=float(p["confidence"]),
            mood=str(p["mood"]),
        )
        for p in raw.get("picks", [])
    ]
    no_clips_reason = str(raw.get("no_clips_reason") or "").strip()

    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    pricing = _PRICING.get(model, {"in": 0, "out": 0})
    cost = (tokens_in / 1_000_000) * pricing["in"] + (tokens_out / 1_000_000) * pricing["out"]

    return EditorialResult(
        picks=picks,
        no_clips_reason=no_clips_reason,
        model=model,
        prompt_version=prompt_version,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=round(cost, 4),
        latency_sec=round(latency, 2),
    )


async def call_editorial_async(topic_context_block: str,
                               anchored_transcript: str,
                               breakpoint_table: str,
                               *,
                               model: str = SONNET_MODEL,
                               prompt_version: str = "v1",
                               max_tokens: int = 4000) -> EditorialResult:
    """Async wrapper — runs the sync call on a worker thread. Use with
    asyncio.gather() to run all topic calls in parallel."""
    return await asyncio.to_thread(
        call_editorial_sync,
        topic_context_block, anchored_transcript, breakpoint_table,
        model=model, prompt_version=prompt_version, max_tokens=max_tokens,
    )


def estimate_cost(tokens_in: int, tokens_out: int, model: str = SONNET_MODEL) -> float:
    pricing = _PRICING.get(model, {"in": 0, "out": 0})
    return round(
        (tokens_in / 1_000_000) * pricing["in"] + (tokens_out / 1_000_000) * pricing["out"],
        4,
    )


def serialize_pick(p: ClipPick) -> dict:
    """JSON-friendly form, used by extract.py for logging."""
    return {
        "start_b": p.start_b,
        "end_b": p.end_b,
        "title": p.title,
        "hook_line": p.hook_line,
        "payoff_summary": p.payoff_summary,
        "single_topic_confirmation": p.single_topic_confirmation,
        "confidence": p.confidence,
        "mood": p.mood,
    }
