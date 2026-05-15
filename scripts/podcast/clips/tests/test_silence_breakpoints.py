"""Tests for silence_breakpoints — pure-function paths only, no ffmpeg invocation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add scripts/ to path so we can import the package
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from podcast.clips.silence_breakpoints import (
    BREAKPOINT_MIN_DURATION_SEC,
    Breakpoint,
    _density_per_minute,
    _filter_to_breakpoints,
)


def test_breakpoint_mid_sec():
    bp = Breakpoint(idx=0, start=10.0, end=11.5, duration=1.5)
    assert bp.mid_sec == 10.75


def test_filter_drops_short_silences():
    # Mix of qualifying and below-threshold silences
    raw = [
        {"start": 1.0, "end": 1.20, "duration": 0.20},   # too short
        {"start": 5.0, "end": 5.50, "duration": 0.50},   # qualifies
        {"start": 8.0, "end": 8.30, "duration": 0.30},   # too short
        {"start": 12.0, "end": 12.95, "duration": 0.95}, # qualifies
        {"start": 20.0, "end": 20.45, "duration": 0.45}, # exactly at threshold
    ]
    bps = _filter_to_breakpoints(raw)
    assert len(bps) == 3
    assert all(bp.duration >= BREAKPOINT_MIN_DURATION_SEC for bp in bps)
    # Indices assigned chronologically starting at 0
    assert [bp.idx for bp in bps] == [0, 1, 2]
    # Sorted by start
    assert bps[0].start == 5.0
    assert bps[2].start == 20.0


def test_filter_handles_empty():
    assert _filter_to_breakpoints([]) == []


def test_density_calculation():
    # 6 breakpoints across 60 seconds = 6 per minute
    bps = [Breakpoint(i, i*10.0, i*10.0+0.5, 0.5) for i in range(6)]
    assert _density_per_minute(bps, 60.0) == 6.0
    # Edge case: zero duration
    assert _density_per_minute(bps, 0.0) == 0.0
    # 3 breakpoints in 600 seconds = 0.3 per minute (very sparse)
    bps3 = [Breakpoint(i, i*100.0, i*100.0+1.0, 1.0) for i in range(3)]
    assert _density_per_minute(bps3, 600.0) == 0.3


def test_filter_re_indexes_after_sort():
    # Pass in unsorted; result should be sorted by start with sequential idx
    raw = [
        {"start": 30.0, "end": 30.60, "duration": 0.60},
        {"start": 10.0, "end": 10.55, "duration": 0.55},
        {"start": 20.0, "end": 20.50, "duration": 0.50},
    ]
    bps = _filter_to_breakpoints(raw)
    assert [bp.start for bp in bps] == [10.0, 20.0, 30.0]
    assert [bp.idx for bp in bps] == [0, 1, 2]
