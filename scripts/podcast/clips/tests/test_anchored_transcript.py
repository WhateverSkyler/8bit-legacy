"""Tests for anchored_transcript — verifies [Bi:T/D] insertion, punctuation
stripping, and the breakpoint table format."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from podcast.clips.anchored_transcript import (
    _clean_word,
    build_anchored_transcript,
    build_breakpoint_table,
)
from podcast.clips.silence_breakpoints import Breakpoint


FIXTURE = Path(__file__).parent / "fixtures" / "tiny_topic.json"


def _load_tiny():
    return json.loads(FIXTURE.read_text())


def test_clean_word_strips_punctuation():
    assert _clean_word(" gaming.") == " gaming"
    assert _clean_word(" penny,") == " penny"
    assert _clean_word(" what?!") == " what"
    assert _clean_word(" and") == " and"
    assert _clean_word("") == ""
    assert _clean_word(" ;:.") == ""


def test_anchored_transcript_inserts_markers_at_silences():
    transcript = _load_tiny()
    # Three breakpoints at the gaps between segments
    breakpoints = [
        Breakpoint(idx=0, start=4.30, end=6.40, duration=2.10),    # between seg 1 and 2
        Breakpoint(idx=1, start=12.70, end=20.90, duration=8.20),  # between seg 2 and 3
        Breakpoint(idx=2, start=28.80, end=39.90, duration=11.10), # between seg 3 and 4
    ]
    text = build_anchored_transcript(transcript, breakpoints)

    # Markers should be present in chronological order
    b0 = text.find("[B0:")
    b1 = text.find("[B1:")
    b2 = text.find("[B2:")
    assert 0 < b0 < b1 < b2

    # Each marker shows midpoint and duration with two-decimal precision
    assert "[B0:5.35/2.10]" in text
    assert "[B1:16.80/8.20]" in text
    assert "[B2:34.35/11.10]" in text

    # Punctuation should be stripped
    assert "gaming." not in text
    assert "penny." not in text
    assert "consoles." not in text


def test_anchored_transcript_handles_no_breakpoints():
    transcript = _load_tiny()
    text = build_anchored_transcript(transcript, [])
    assert "[B" not in text
    assert "welcome" in text


def test_anchored_transcript_handles_empty_transcript():
    text = build_anchored_transcript({"segments": []}, [])
    assert text == ""


def test_breakpoint_table_format():
    breakpoints = [
        Breakpoint(idx=0, start=10.0, end=11.0, duration=1.0),
        Breakpoint(idx=1, start=20.0, end=20.55, duration=0.55),
    ]
    table = build_breakpoint_table(breakpoints)
    assert "B0" in table
    assert "B1" in table
    assert "10.50" in table
    assert "20.27" in table or "20.28" in table  # rounding tolerance
    assert "d=1.00" in table
    assert "d=0.55" in table


def test_breakpoint_table_empty_explanation():
    table = build_breakpoint_table([])
    assert "no breakpoints" in table


def test_anchored_marker_lands_after_silence_ends():
    """A breakpoint Bi should appear AFTER the last word that ends before Bi.end,
    and BEFORE the next word that starts at or after Bi.end."""
    transcript = _load_tiny()
    # One breakpoint spanning a clear silence (4.20 → 6.50 between words)
    breakpoints = [Breakpoint(idx=0, start=4.30, end=6.40, duration=2.10)]
    text = build_anchored_transcript(transcript, breakpoints)
    # "gaming" is the last word before the silence, "specifically" is the first after
    gaming_idx = text.find("gaming")
    marker_idx = text.find("[B0:")
    spec_idx = text.find("specifically")
    assert gaming_idx < marker_idx < spec_idx
