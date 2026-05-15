"""Tests for verify — structural validation, duration band, IoU dedup,
title truncation, clip_id assignment."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from podcast.clips.editorial_call import ClipPick
from podcast.clips.silence_breakpoints import Breakpoint
from podcast.clips.topic_context import TopicContext
from podcast.clips.verify import (
    DURATION_CEILING_SEC,
    DURATION_FLOOR_SEC,
    _iou,
    _truncate_on_word_boundary,
    verify,
)


def _bp(idx, start, end):
    return Breakpoint(idx=idx, start=start, end=end, duration=end - start)


def _ctx(duration=600.0):
    return TopicContext(slug="test-topic", title_hint="Test", thesis="",
                        subtopics=(), duration_sec=duration)


def _pick(start_b, end_b, title="A great clip", confidence=0.8, mood="reflective"):
    return ClipPick(start_b=start_b, end_b=end_b, title=title,
                    hook_line="hook", payoff_summary="payoff",
                    single_topic_confirmation="topic", confidence=confidence, mood=mood)


def test_truncate_on_word_boundary():
    # Already short
    assert _truncate_on_word_boundary("Short title", max_chars=60) == "Short title"
    # Long title — should cut at a word boundary, not mid-word
    long_title = "This is a very long title that goes well past the maximum allowed character count"
    out = _truncate_on_word_boundary(long_title, max_chars=40)
    assert len(out) <= 40
    assert " " in out  # didn't cut mid-word
    assert not out.endswith(",") and not out.endswith(":")


def test_iou_calculation():
    assert _iou(0, 10, 0, 10) == 1.0
    assert _iou(0, 10, 5, 15) == 5 / 15  # union 0-15, intersection 5-10
    assert _iou(0, 10, 20, 30) == 0.0
    assert _iou(0, 10, 10, 20) == 0.0  # touching but not overlapping


def test_verify_drops_invalid_indices():
    bps = [_bp(0, 5.0, 6.0), _bp(1, 30.0, 31.0)]
    picks = [
        _pick(start_b=0, end_b=5),   # end_b out of range
        _pick(start_b=2, end_b=3),   # both out of range
        _pick(start_b=1, end_b=0),   # end_b <= start_b
    ]
    out = verify(picks, bps, _ctx(), source_stem="test_stem",
                 model="claude-sonnet-4-6", prompt_version="v1")
    assert len(out.specs) == 0
    assert len(out.dropped) == 3
    assert all("invalid_index" in d.reason for d in out.dropped)


def test_verify_drops_too_short():
    bps = [_bp(0, 5.0, 5.5), _bp(1, 14.0, 14.5)]   # would yield ~9s clip
    picks = [_pick(start_b=0, end_b=1)]
    out = verify(picks, bps, _ctx(), source_stem="test", model="m", prompt_version="v1")
    assert len(out.specs) == 0
    assert "duration_out_of_band" in out.dropped[0].reason


def test_verify_drops_too_long():
    bps = [_bp(0, 5.0, 5.5), _bp(1, 100.0, 100.5)]  # ~95s clip, over 90s cap
    picks = [_pick(start_b=0, end_b=1)]
    out = verify(picks, bps, _ctx(), source_stem="test", model="m", prompt_version="v1")
    assert len(out.specs) == 0
    assert "duration_out_of_band" in out.dropped[0].reason


def test_verify_keeps_in_band():
    bps = [_bp(0, 5.0, 5.5), _bp(1, 50.0, 50.5)]   # ~45s clip
    picks = [_pick(start_b=0, end_b=1, title="A great clip about gaming")]
    out = verify(picks, bps, _ctx(), source_stem="ep1_topic2_1080p",
                 model="claude-sonnet-4-6", prompt_version="v1")
    assert len(out.specs) == 1
    spec = out.specs[0]
    assert spec["clip_id"] == "ep1_topic2_1080p_c1"
    assert spec["source_stem"] == "ep1_topic2_1080p"
    assert spec["duration_sec"] == round(spec["end_sec"] - spec["start_sec"], 2)
    assert DURATION_FLOOR_SEC <= spec["duration_sec"] <= DURATION_CEILING_SEC
    assert spec["title"] == "A great clip about gaming"
    assert spec["model"] == "claude-sonnet-4-6"
    assert "youtube_shorts" in spec["platform_eligibility"]


def test_verify_assigns_clip_ids_chronologically():
    bps = [_bp(0, 5.0, 5.5), _bp(1, 35.0, 35.5),
           _bp(2, 100.0, 100.5), _bp(3, 130.0, 130.5),
           _bp(4, 200.0, 200.5), _bp(5, 230.0, 230.5)]
    picks = [
        _pick(start_b=4, end_b=5, title="Third one"),    # latest
        _pick(start_b=0, end_b=1, title="First one"),    # earliest
        _pick(start_b=2, end_b=3, title="Middle one"),
    ]
    out = verify(picks, bps, _ctx(), source_stem="stem",
                 model="m", prompt_version="v1")
    assert len(out.specs) == 3
    assert out.specs[0]["clip_id"] == "stem_c1"
    assert out.specs[1]["clip_id"] == "stem_c2"
    assert out.specs[2]["clip_id"] == "stem_c3"
    assert out.specs[0]["title"] == "First one"
    assert out.specs[2]["title"] == "Third one"


def test_verify_dedup_keeps_higher_confidence():
    bps = [_bp(0, 5.0, 5.5), _bp(1, 50.0, 50.5),
           _bp(2, 6.0, 6.5), _bp(3, 51.0, 51.5)]   # mostly overlapping
    picks = [
        _pick(start_b=0, end_b=1, title="Lower conf", confidence=0.6),
        _pick(start_b=2, end_b=3, title="Higher conf", confidence=0.9),
    ]
    out = verify(picks, bps, _ctx(), source_stem="stem", model="m", prompt_version="v1")
    assert len(out.specs) == 1
    assert out.specs[0]["title"] == "Higher conf"


def test_verify_keeps_non_overlapping_picks():
    bps = [_bp(0, 5.0, 5.5), _bp(1, 50.0, 50.5),
           _bp(2, 100.0, 100.5), _bp(3, 145.0, 145.5)]
    picks = [
        _pick(start_b=0, end_b=1),
        _pick(start_b=2, end_b=3),
    ]
    out = verify(picks, bps, _ctx(), source_stem="stem", model="m", prompt_version="v1")
    assert len(out.specs) == 2


def test_verify_assigns_music_volume_from_mood():
    bps = [_bp(0, 5.0, 5.5), _bp(1, 50.0, 50.5)]
    for mood, expected_vol in [
        ("chill", 0.10), ("reflective", 0.10),
        ("funny", 0.12), ("hopeful", 0.12),
        ("hype", 0.14), ("heated", 0.14),
    ]:
        picks = [_pick(start_b=0, end_b=1, mood=mood)]
        out = verify(picks, bps, _ctx(), source_stem="stem", model="m", prompt_version="v1")
        assert out.specs[0]["_audio_music_volume"] == expected_vol
        assert out.specs[0]["_audio_mood"] == mood


def test_verify_drops_past_eof():
    # Topic only 30s long, but breakpoint pair would yield clip ending past it
    bps = [_bp(0, 5.0, 5.5), _bp(1, 35.0, 35.5)]
    picks = [_pick(start_b=0, end_b=1)]
    out = verify(picks, bps, _ctx(duration=30.0), source_stem="stem", model="m", prompt_version="v1")
    # Duration would be ~30s (in band), but end_sec ~35.55 > topic 30 + 0.5
    assert len(out.specs) == 0
    assert any("past_eof" in d.reason for d in out.dropped)
