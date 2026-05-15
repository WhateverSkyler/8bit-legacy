"""Audio-waveform silence detection for clip end-boundary placement.

Round 14 (2026-05-14): rebuilt end-boundary placement to use REAL audio silence
instead of text-derived sentence boundaries. The previous text-based approach
(round 13: HIGH/MED/LOW sentence boundary_confidence + safe_breath_pad +
0.10s safety margin) kept producing clips that cut mid-word in the audio,
because whisperX word timing isn't audio-aligned to actual silence and
"sentences" with 0.5-1.0s text-gaps can have continuous speech audio between
them (the speaker's breath/room tone is louder than -30dB).

This module's job: identify the REAL pause points in an episode's audio via
ffmpeg silencedetect, cache them per-episode, and provide a lookup that
returns clip-end timestamps guaranteed to land in actual silence.

Threshold tuning (May 5 2026 episode sweep):
- -30dB catches breath/HVAC noise → 1139 events for 67min episode (too many).
- -35dB:d=0.20 → 654 events (≈10/min, ~one per 6s, matches natural pause density).
- -40dB:d=0.25 → 261 events (some real conversational pauses get missed).

Picked -35dB:d=0.20 for the wide net. Strict end-boundary picking then
filters to silence_duration ≥ MIN_END_SILENCE_SEC (0.30s) — REAL pauses, not
mid-word stops.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# ----------------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------------
SILENCE_DB = -35              # ffmpeg silencedetect noise floor
SILENCE_MIN_DUR = 0.20        # min silence duration the detector reports (seconds)

# For clip-end placement we require LONGER silences than the detector's floor.
# A 0.20s "silence" is often a mid-word stop on a hard consonant; we want a
# real pause where the speaker has finished a thought.
MIN_END_SILENCE_SEC = 0.30

# Round 17 (2026-05-14): the end-completion GATE (Claude judgment over
# multiple candidates) can consider slightly tighter pauses than the
# first-pass _snap_and_validate placement. Reason: when the gate is
# EXTENDing to capture a payoff (e.g., "guess which franchise → Mario"),
# the answer-landing silence is sometimes shorter than the setup-landing
# silence. Strict 0.30s threshold for _snap_and_validate keeps initial
# placement clean; relaxed 0.22s for gate candidates gives Claude more
# options without lowering the bar for clips with no over-extension.
GATE_END_MIN_SILENCE_SEC = 0.22

# Offset into the silence period at which the clip ends. 100ms gives the audio
# a clean tail of post-word silence before the visual/audio fade kicks in.
END_OFFSET_INTO_SILENCE = 0.10

# Round 20 (2026-05-14): silence classifier thresholds — distinguish
# sentence-end silences from mid-sentence breath pauses by combining audio
# duration with the transcript-side punctuation signal.
# Loosened on first calibration pass against May 5 episode (only 9% of
# whisperX words carry terminal punctuation, so we can't rely on text alone).
LONG_PAUSE_FOR_SENTENCE_END = 0.55       # any pause ≥ this is a real boundary regardless of text
MEDIUM_PAUSE_WITH_PUNCT_SEC = 0.30       # 0.30–0.55s pauses count only if prev word ends with .!?
SHORT_PAUSE_WITH_PUNCT_AND_GAP_SEC = 0.22  # 0.22–0.30s pauses count only with strong text signal
SENTENCE_END_TERMINAL_PUNCT = ('.', '!', '?')

# Format string for the disk-cache params field. If this changes, caches
# invalidate automatically.
PARAMS_FINGERPRINT = f"{SILENCE_DB}dB:d={SILENCE_MIN_DUR}"

_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END_RE = re.compile(
    r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)"
)


# ----------------------------------------------------------------------------
# Cache infrastructure
# ----------------------------------------------------------------------------
def _cache_path_for(audio_path: Path) -> Path:
    """Cache lives next to the audio file as <stem>.silence.json. Keeps the
    1:1 mapping between audio and silence map (re-encoded audio invalidates
    cleanly), and avoids assuming a transcripts/ sibling directory exists."""
    return audio_path.parent / f"{audio_path.stem}.silence.json"


def _cache_key(audio_path: Path) -> dict:
    """Composite key: file mtime + size + ffmpeg params fingerprint.

    Re-encoded source (different bytes), threshold tuning (different
    fingerprint), or moved/touched file (different mtime) all invalidate.
    """
    st = audio_path.stat()
    return {
        "audio_mtime": st.st_mtime,
        "audio_size": st.st_size,
        "params": PARAMS_FINGERPRINT,
    }


def _load_cache(cache_file: Path, expected_key: dict) -> list[dict] | None:
    if not cache_file.exists():
        return None
    try:
        blob = json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(blob, dict):
        return None
    if blob.get("audio_mtime") != expected_key["audio_mtime"]:
        return None
    if blob.get("audio_size") != expected_key["audio_size"]:
        return None
    if blob.get("params") != expected_key["params"]:
        return None
    periods = blob.get("periods")
    if not isinstance(periods, list):
        return None
    return periods


def _save_cache(cache_file: Path, key: dict, periods: list[dict]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {**key, "periods": periods}
    cache_file.write_text(json.dumps(payload, indent=2))


# ----------------------------------------------------------------------------
# silencedetect runner
# ----------------------------------------------------------------------------
def _run_silencedetect(audio_path: Path) -> list[dict]:
    """Run ffmpeg silencedetect on the file, parse stderr, return periods.

    ffmpeg's silencedetect emits one start line + one end line per silence
    period. Output goes to stderr. We pair them by order — the format is
    deterministic.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(audio_path),
        "-af", f"silencedetect=n={SILENCE_DB}dB:d={SILENCE_MIN_DUR}",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    starts: list[float] = []
    ends: list[tuple[float, float]] = []  # (end_t, duration)
    for line in proc.stderr.splitlines():
        m = _SILENCE_START_RE.search(line)
        if m:
            starts.append(float(m.group(1)))
            continue
        m = _SILENCE_END_RE.search(line)
        if m:
            ends.append((float(m.group(1)), float(m.group(2))))
    # Pair by order; if mismatched (shouldn't happen), truncate to min length.
    n = min(len(starts), len(ends))
    return [
        {"start": starts[i], "end": ends[i][0], "duration": ends[i][1]}
        for i in range(n)
    ]


def compute_silence_map(audio_path: Path) -> list[dict]:
    """Return list of silence periods (start, end, duration) for the given
    audio file. Cached on disk by mtime+size+params.

    `audio_path` should be the 1080p source mp4 (dialogue-only — no music
    is mixed in until render time, so silencedetect sees real audio pauses).
    """
    cache_file = _cache_path_for(audio_path)
    key = _cache_key(audio_path)
    cached = _load_cache(cache_file, key)
    if cached is not None:
        return cached
    periods = _run_silencedetect(audio_path)
    _save_cache(cache_file, key, periods)
    return periods


# ----------------------------------------------------------------------------
# Round 20 (2026-05-14): SILENCE CLASSIFIER
# Combine audio (silence duration) + transcript (prior word's punctuation,
# gap to next word) signals to distinguish sentence-end silences from
# mid-sentence breath pauses. Mid-sentence silences are NOT valid clip
# endpoints.
# ----------------------------------------------------------------------------

def _build_word_index(transcript: dict) -> list[dict]:
    """Flatten transcript segments into a sorted word list with start/end/text.
    Used by `classify_silence` to look up surrounding words for each silence
    period. Cheap — called once per episode.
    """
    words: list[dict] = []
    for seg in transcript.get("segments", []):
        for w in seg.get("words") or []:
            txt = (w.get("word") or "").strip()
            if not txt:
                continue
            try:
                start = float(w.get("start", 0.0))
                end = float(w.get("end", 0.0))
            except (TypeError, ValueError):
                continue
            words.append({"start": start, "end": end, "text": txt})
    words.sort(key=lambda x: x["start"])
    return words


def _find_word_ending_before(t: float, words: list[dict]) -> dict | None:
    """Return the word whose `end` is closest to (and ≤ t + small epsilon).
    Binary search would be faster but the linear scan is fine for ~10k words."""
    best = None
    for w in words:
        if w["end"] <= t + 0.05:
            best = w
        else:
            break
    return best


def _find_word_starting_after(t: float, words: list[dict]) -> dict | None:
    """Return the first word whose `start` is ≥ t - small epsilon."""
    for w in words:
        if w["start"] >= t - 0.05:
            return w
    return None


def classify_silence(silence: dict, words: list[dict]) -> str:
    """Classify a silence period as 'sentence-end' or 'mid-sentence' based on
    combined audio (silence duration) and transcript (punctuation + gap) signals.

    Rules — all combine audio + text signals (no keyword lists, no
    video-specific patterns):

      1. silence_duration ≥ 0.70s → 'sentence-end'
         Long pauses are intentional conversational boundaries regardless
         of whether the transcript captured punctuation.

      2. silence_duration ≥ 0.35s AND prev_word ends with .!? → 'sentence-end'
         Medium pause + explicit punctuation signal = real sentence boundary.

      3. silence_duration ≥ 0.25s AND prev_word ends with .!?
         AND (next_word.start - silence.end) ≥ 0.05 → 'sentence-end'
         Short but bounded by both signals.

      4. Otherwise → 'mid-sentence'
         Likely a breath pause or emphasis pause inside a single thought.
    """
    dur = float(silence.get("duration", 0.0))
    prev_w = _find_word_ending_before(silence["start"], words)
    next_w = _find_word_starting_after(silence["end"], words)

    has_terminal_punct = bool(prev_w and
        prev_w["text"].rstrip('"\'').endswith(SENTENCE_END_TERMINAL_PUNCT))

    if dur >= LONG_PAUSE_FOR_SENTENCE_END:
        return "sentence-end"
    if dur >= MEDIUM_PAUSE_WITH_PUNCT_SEC and has_terminal_punct:
        return "sentence-end"
    if dur >= SHORT_PAUSE_WITH_PUNCT_AND_GAP_SEC and has_terminal_punct:
        # If we also have a measurable gap between silence-end and next word
        # (i.e., the speaker didn't restart immediately), it's a real boundary.
        if next_w is None or next_w["start"] - silence["end"] >= 0.02:
            return "sentence-end"
    return "mid-sentence"


def sentence_end_silences(silence_map: list[dict], transcript: dict) -> list[dict]:
    """Return only the silence periods classified as 'sentence-end' boundaries.

    Each returned dict is the original silence period augmented with
    `_classification: 'sentence-end'`. Mid-sentence breath pauses are
    omitted entirely — invisible to downstream gate logic so the clip-end
    snap can NEVER land at a mid-sentence pause.

    Cached on the transcript dict under `_sentence_end_silences` so this
    runs once per episode regardless of how many gate calls need it.
    """
    cache_key = f"_sentence_end_silences_{id(silence_map)}"
    cached = transcript.get(cache_key)
    if cached is not None:
        return cached
    words = _build_word_index(transcript)
    filtered: list[dict] = []
    n_sent = n_mid = 0
    for s in silence_map:
        cls = classify_silence(s, words)
        if cls == "sentence-end":
            filtered.append({**s, "_classification": "sentence-end"})
            n_sent += 1
        else:
            n_mid += 1
    transcript[cache_key] = filtered
    print(f"  [silence] classified {len(silence_map)} periods → "
          f"{n_sent} sentence-end, {n_mid} mid-sentence (filtered out)")
    return filtered


# ----------------------------------------------------------------------------
# Boundary lookup
# ----------------------------------------------------------------------------
def best_end_in_window(silence_map: list[dict], target_end: float,
                       search_lo: float, search_hi: float,
                       min_silence: float = MIN_END_SILENCE_SEC) -> float | None:
    """Return the clip-end timestamp closest to `target_end` that lands in
    real audio silence within [search_lo, search_hi].

    Filters silence_map to periods with `duration >= min_silence` (real
    pauses, not consonant stops) whose `start` is inside the window.
    Picks the one whose start is closest to target_end; on ties, prefers
    the LONGER silence period (more emphatic landing).

    Returns silence["start"] + END_OFFSET_INTO_SILENCE (100ms into silence
    so the clip end has a clean post-word tail before fade).

    Returns None if no qualifying silence exists. Caller should widen the
    window or REJECT the pick — do NOT fall back to text-based snapping
    (the broken path this module exists to replace).
    """
    qualifying = [
        s for s in silence_map
        if search_lo <= s["start"] <= search_hi and s["duration"] >= min_silence
    ]
    if not qualifying:
        return None
    qualifying.sort(key=lambda s: (abs(s["start"] - target_end), -s["duration"]))
    chosen = qualifying[0]
    return chosen["start"] + END_OFFSET_INTO_SILENCE


def nearest_silence_at_or_after(silence_map: list[dict], target_t: float,
                                forward_window: float = 0.5,
                                back_window: float = 0.5,
                                min_duration: float = GATE_END_MIN_SILENCE_SEC,
                                ) -> float | None:
    """Round 19.5 (2026-05-14): land the clip end AT Claude's semantic
    conclusion timestamp, snapping to a nearby real audio silence ONLY if
    one exists very close (±0.5s).

    Critical: Claude's target_t is the end-of-last-word it wants included.
    Snapping to a silence MUCH later than target (e.g., +4s) means playing
    through 4 seconds of content Claude did NOT mean to include — likely a
    new sentence. That's the user-reported r19.0 failure mode ("EVERY
    video cuts off mid-sentence").

    Rules:
      1. If target_t is INSIDE a silence period [start, end]:
         → land at max(target_t, silence_start + 0.10), never earlier than target_t.
      2. If silence exists JUST AFTER target_t (≤ 0.5s forward) with
         duration ≥ min_duration:
         → land at silence_start + 0.10s.
      3. If target_t is just PAST a silence end (≤ 0.5s, silence_end < target_t):
         → land at target_t + 0.05 (essentially the target with a tiny tail).
      4. Otherwise:
         → return None — caller should fall back to using target_t directly.
            Better to clip a trailing consonant by a few ms than play 4s
            of unwanted content past Claude's intended end.
    """
    forward: dict | None = None
    for s in silence_map:
        if s["duration"] < min_duration:
            continue
        s_start = s["start"]
        s_end = s["end"]
        # 1. Target is INSIDE this silence period.
        if s_start <= target_t <= s_end + 0.05:
            proposed = s_start + END_OFFSET_INTO_SILENCE
            return max(proposed, target_t)
        # 2. Silence is just forward of target.
        if target_t < s_start <= target_t + forward_window:
            forward = s
            break  # silence_map is sorted; first hit is closest forward
        # No useful 'before' case — if silence ends before target_t, the
        # last word starts after that silence, so landing in silence cuts
        # the last word. Skip.
    if forward is not None:
        return forward["start"] + END_OFFSET_INTO_SILENCE
    return None


def silence_candidates_for_gate(silence_map: list[dict],
                                lo: float, hi: float,
                                min_silence: float = MIN_END_SILENCE_SEC,
                                max_n: int = 6) -> list[dict]:
    """Return the silence periods within [lo, hi] that qualify as candidate
    clip-ends, sorted by START time ascending. Used by `_end_completion_gate`
    to show Claude a set of silence-aligned ending options to choose from.

    Each returned dict has:
      start:     silence_start (seconds)
      end:       silence_end (seconds)
      duration:  silence duration (seconds)
      clip_end:  start + END_OFFSET_INTO_SILENCE (where the clip would end)
    """
    qualifying = [
        {**s, "clip_end": s["start"] + END_OFFSET_INTO_SILENCE}
        for s in silence_map
        if lo <= s["start"] <= hi and s["duration"] >= min_silence
    ]
    qualifying.sort(key=lambda s: s["start"])
    return qualifying[:max_n]
