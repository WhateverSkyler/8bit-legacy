"""Prompts for the four shorts QA gates.

Versioned independently from logic so we can iterate the wording without touching
flow code. Each constant ends in _V1 — when we tune, bump to _V2 and keep both
so we can A/B compare results from old runs.

Gates in order:
  GATE_1_NARRATIVE_COHERENCE_V1 — text-only, post-pick re-validation
  GATE_2_CAPTION_SYNC_V1        — multimodal, post-render
  GATE_3_FRAMING_V1             — multimodal, post-render
  GATE_4_FINAL_APPROVAL_V1      — multimodal, pre-schedule (Opus)
"""

# =====================================================================
# GATE 0 — Topic coherence at segmentation time (text only, pre-pick)
# =====================================================================
# Catches the "lumpy topic" failure mode at the SOURCE — a topic that
# auto-segmentation tagged as "Black Flag pricing debate" but actually
# spans three unrelated discussions. Existing 4 gates downstream can't
# fully fix this — if the topic itself is incoherent, no clip from it
# will be coherent.

GATE_0_TOPIC_COHERENCE_V1 = """You are auditing a topic-segmented chunk from a podcast for coherence.

Auto-segmentation thinks this section is one coherent topic with the title and
thesis below. Your job: does the transcript text actually support that, or does
it span multiple unrelated subjects that should have been split?

TOPIC TITLE: {title}
TOPIC THESIS: {thesis}
DURATION: {duration_sec:.1f}s ({duration_min:.1f} min)
RANGE: {start_sec:.1f}s – {end_sec:.1f}s

TRANSCRIPT TEXT:
\"\"\"
{transcript_text}
\"\"\"

EVALUATE:

1. **Single coherent topic** — does the entire transcript discuss the title's subject?
   - PASS: text follows the thesis throughout, with on-topic tangents
   - SPLIT: clearly switches to a different subject mid-way (e.g., starts on Black Flag,
            then tangents into Resident Evil for the second half)
   - INCOHERENT: never really lands on a topic, just rambles across subjects

2. **Title-thesis-content match**:
   - Does the title accurately describe what's discussed?
   - Does the thesis hold throughout the segment?

3. **Split opportunity** (only if you marked SPLIT):
   - Identify the approximate timestamp (in seconds, as positioned in the
     transcript range provided) where one subject ends and the next begins.

DECISION RULES:
- All on-topic OR mostly-on-topic with minor tangents → PASS
- Clear topic shift mid-way → SPLIT (provide proposed split timestamp)
- Rambles across multiple subjects with no clear primary → INCOHERENT (drop topic)

Return STRICT JSON only:
{{
  "decision": "PASS" | "SPLIT" | "INCOHERENT",
  "primary_subject": "what the topic IS actually about, in 1 line",
  "secondary_subjects": ["if SPLIT: list of other subjects covered"],
  "split_timestamp_sec": null | <float, only if SPLIT, ABSOLUTE seconds in source>,
  "title_match": "good" | "vague" | "wrong",
  "thesis_holds": <bool>,
  "reason": "one-sentence summary"
}}
"""


# =====================================================================
# GATE 1 — Narrative coherence re-validation (text only)
# =====================================================================

GATE_1_NARRATIVE_COHERENCE_V1 = """You are a stand-alone-ness auditor for short-form video clips.

A clip is being considered for publishing on TikTok / Reels / YouTube Shorts. A viewer
who has NEVER watched the source podcast before will see ONLY the extracted text below
(plus the burned captions and audio in the rendered video). Your job: decide if this
clip works as a stand-alone short OR if it has issues that would lose the viewer.

CLIP CANDIDATE:
  Title: {title}
  Hook: {hook}
  Topics: {topics}
  Duration: {duration_sec:.1f}s
  Boundaries: {start_sec:.2f}s – {end_sec:.2f}s

EXTRACTED CLIP TEXT (this is what the viewer hears + sees as captions):
\"\"\"
{extracted_text}
\"\"\"

FOR CONTEXT — surrounding transcript text (the viewer does NOT see this — but you
need it to judge whether the clip's opening is self-contained or relies on prior context):
\"\"\"
{surrounding_context}
\"\"\"

EVALUATE ON 4 DIMENSIONS:

1. **Opening sets context** — first 2 sentences:
   - No unresolved pronouns ("he was saying that..." is BAD if "he" wasn't introduced)
   - No conjunction openers ("yeah", "and", "so", "but", "then")
   - No filler agreement ("right", "exactly", "totally")
   - No mid-thought markers ("like I said", "you know what I mean")
   - The opening introduces the topic OR the take being made

2. **Complete arc** — setup → payoff:
   - There's an actual claim, story, or argument being made (not just casual chatter)
   - The clip ends with a conclusion, punchline, hot take, or natural turn-of-page
   - NOT setup-without-payoff ("here's a wild story... and that's all" — REJECT)
   - NOT payoff-without-setup (just a punchline that requires context — REJECT)

3. **Hook lands in first 5 seconds**:
   - First 5 seconds (~12-15 words) must do ONE of:
     a) State an opinion / hot take ("Nintendo is making a huge mistake")
     b) Drop a surprising fact ("Game budgets have tripled in 5 years")
     c) Pose curiosity ("You think you know Zelda but here's the truth about Wind Waker")
     d) Set up a story with stakes ("So I traded my entire console collection for...")
   - First 5 seconds is JUST exposition / preamble = ENGAGEMENT RISK HIGH = REJECT for shorts

4. **Clean ending**:
   - Last 3 seconds wraps up the thought
   - NOT trailing off ("...yeah, anyway"), NOT mid-sentence cut, NOT teasing more

DECISION RULES (CALIBRATED 2026-05-08 — bias toward shipping watchable content):
- 0-1 dimensions fail → PASS (podcast clips don't need perfection on every dimension)
- 2 dimensions fail AND adjustment would fix at least one (e.g., extending boundaries by
  10s captures missing setup) → return ADJUST with proposed boundaries
- 3+ dimensions fail OR clip is genuinely incomprehensible alone → REJECT

If you adjust: only return new boundaries if you have HIGH confidence the new range
improves things. Otherwise PASS as-is — Gate 4 will make the final call.

Treat "no clear punchy hook" as a FAIL only on the engagement_risk dimension (set "high")
but DON'T reject on this alone — many good podcast clips are conversational and don't
need a punchy hook. Reject only on full-comprehensibility failures.

Return STRICT JSON only:
{{
  "passes": <bool>,
  "decision": "PASS" | "ADJUST" | "REJECT",
  "adjusted_boundaries": null | {{"start_sec": <float>, "end_sec": <float>}},
  "hook_in_first_5_sec": <bool>,
  "hook_type": "opinion" | "fact" | "curiosity" | "story_setup" | "exposition_only" | "none",
  "engagement_risk": "low" | "medium" | "high",
  "issues": ["specific failure descriptions, if any"],
  "reason": "one-sentence summary"
}}
"""


# =====================================================================
# GATE 2 — Caption-audio sync (multimodal)
# =====================================================================

GATE_2_CAPTION_SYNC_V1 = """You are auditing burned captions for sync with audio in a short-form video.

I've extracted 2 keyframes from the rendered MP4 — one near the START of the clip and
one near the END. Your task: judge whether the burned captions match what the speaker
is actually saying, AND whether the captions are properly synced with lip movement.

CLIP CONTEXT:
  Title: {title}
  Duration: {duration_sec:.1f}s
  Word timings (first 30 words from transcript):
{word_timings_excerpt}

CHECKS:
1. **Caption text accuracy**: Read the captions visible in the keyframes. Do they look
   like coherent English that matches the apparent topic of the clip? Look for:
   - Garbled / nonsensical word sequences (transcript noise)
   - Words that don't match the clip's claimed topic
   - Repeating words (transcript bug)

2. **Caption-to-lip sync**: Looking at the speaker's mouth in each frame, do the visible
   captions match what their lips appear to be forming? Note: this is hard to judge from
   just 2 frames, so:
   - If both frames clearly show captions that DON'T match what the speaker appears to be
     saying → MISALIGNED
   - If the frames are ambiguous (caption could match) → DRIFT (uncertain)
   - If captions clearly match → GOOD

3. **Silent regions labeled with dialogue**: If you can see the speaker NOT talking but
   captions are showing dialogue → BIG sync problem

DECISION RULES:
- If captions look correct in both frames AND nothing suggests sync issues → PASS
- If captions look slightly off but might be a 1-frame issue → DRIFT (recommend rerender_with_offset)
- If captions are clearly wrong / mismatched → REJECT (mark for human review)

OFFSET SIGN CONVENTION (CRITICAL):
- estimated_offset_sec is the value we'll ADD to every caption timestamp.
- POSITIVE offset = captions shift LATER in time (use when AUDIO IS AHEAD of captions —
  i.e., the speaker's mouth moves first, then the caption appears).
- NEGATIVE offset = captions shift EARLIER (use when CAPTIONS ARE AHEAD of audio).
- Realistic Whisper drift is rarely > 1.0s; values > ±2.0s will be auto-rejected.
- If you can't confidently estimate the offset, use null and recommend "reject" instead.

Return STRICT JSON only:
{{
  "caption_match": <bool>,
  "sync_quality": "good" | "drift" | "misaligned",
  "issues": ["specific issues observed in frames"],
  "recommendation": "pass" | "rerender_with_offset" | "reject",
  "estimated_offset_sec": null | <float, only if rerender_with_offset, in [-2.0, 2.0]>,
  "reason": "one-sentence summary"
}}
"""


# =====================================================================
# GATE 3 — Framing / centering (multimodal)
# =====================================================================

GATE_3_FRAMING_V1 = """You are auditing the framing of a vertical short (1080×1920 portrait).

I've extracted 4 keyframes from across the clip. The clip was rendered with auto-detected
crop offsets per scene (scenes are listed below). Your task: judge whether the speaker is
properly centered in each frame, and whether scene transitions are smooth.

CLIP CONTEXT:
  Title: {title}
  Duration: {duration_sec:.1f}s
  Frame timestamps (matching the 4 keyframes): {frame_timestamps}
  Scene boundaries (start_sec, end_sec, crop_x): {scenes_summary}

CHECKS PER FRAME:
1. **Speaker centered horizontally**: Is the person speaking (or being focused on) within
   the center 80% of the frame width? Specifically:
   - "center" = subject's face midpoint within ±10% of frame center
   - "left" / "right" = subject's face midpoint 10-30% off center (noticeable but not severe)
   - "off_frame" = subject's face is more than 30% off center, OR partially cut off

2. **Subject identity**: In a multi-host podcast, the "speaker" is the person actively
   talking. If the frame shows multiple people, the centered one should be the active speaker.
   If you can't tell → mark "ambiguous".

3. **Frame integrity**: Any visible glitches? Black bars? Cut-off heads? Compression artifacts?
   Mention specifically if seen.

CHECKS ACROSS TRANSITIONS (between consecutive keyframes):
4. **Crop jump quality**: If two consecutive frames are from different scenes (different
   crop_x in scene_summary), does the framing feel smooth or jarring?
   - "smooth": even though the crop changed, the new framing makes sense (different speaker
     or speaker moved)
   - "noticeable_lag": new speaker visible but still off-center for a moment
   - "jarring": crop jumped to wrong position, subject lost

DECISION RULES:
- 0 frames off_frame, 0 jarring transitions → PASS
- 1 frame is "left" or "right" (mild) AND no jarring → PASS with minor warning
- ≥1 frame "off_frame" OR "jarring" transition → REJECT_REFRAME (try stricter scene detection)
- 2+ frames off_frame → REJECT outright (can't be fixed by re-detection)

Return STRICT JSON only:
{{
  "frames": [
    {{
      "pct": <int 0-100, % of duration>,
      "subject_position": "center" | "left" | "right" | "off_frame" | "ambiguous",
      "issue": null | "description"
    }}, ...
  ],
  "transitions": [
    {{
      "between_frames": [<int>, <int>],
      "quality": "smooth" | "noticeable_lag" | "jarring",
      "issue": null | "description"
    }}, ...
  ],
  "overall_quality": "good" | "acceptable" | "poor",
  "recommendation": "pass" | "manual_review" | "reject_reframe" | "reject",
  "reason": "one-sentence summary"
}}
"""


# =====================================================================
# TITLE QUALITY AUDIT (post-pick, text only)
# =====================================================================
# Audits the title pick_clips.py wrote. Catches clickbait, vague filler,
# inaccuracy, and length issues that Gate 4's title-match check doesn't
# explicitly address.

TITLE_QUALITY_AUDIT_V1 = """You audit the title for a short-form video before it goes live.

Title: {title}
Hook: {hook}
Topics: {topics}
Clip text (what viewers will hear, first 1500 chars):
\"\"\"
{extracted_text}
\"\"\"

Score on 4 dimensions:

1. **Specific not vague**: Does the title name the actual subject? "GameStop's
   eBay disaster" PASSES. "An interesting take on retro" FAILS.

2. **Not clickbait**: No "you won't believe", "this changes everything",
   excessive ALL CAPS, or promises the content doesn't deliver.

3. **Length**: 4-12 words ideal. <4 words is usually too vague.
   >12 words is usually overstuffed for a short-form post.

4. **Accurate**: Title describes what's actually said in the clip text. NOT a
   reframing or stretch.

DECISIONS:
- All 4 dimensions PASS → APPROVE
- 1 dimension borderline → APPROVE_WITH_NOTE (still ship, log warning)
- ≥1 dimension fails clearly → REWRITE (return a better title)
- Cannot rewrite without lying → REJECT

Return STRICT JSON only:
{{
  "scores": {{
    "specific": "good" | "borderline" | "fail",
    "not_clickbait": "good" | "borderline" | "fail",
    "length": "good" | "borderline" | "fail",
    "accurate": "good" | "borderline" | "fail"
  }},
  "decision": "APPROVE" | "APPROVE_WITH_NOTE" | "REWRITE" | "REJECT",
  "rewritten_title": null | "<better title if REWRITE>",
  "issues": ["specific issues if any"],
  "reason": "one-sentence summary"
}}
"""


# =====================================================================
# HASHTAG SELECTION (post-pick, text only)
# =====================================================================
# Generate 12-15 RELEVANT hashtags for a clip based on its actual content.
# Replaces the fixed DEFAULT_HASHTAGS list. Keeps algorithm-baseline
# (#fyp/#foryoupage/#explorepage/#shorts) + brand (#8bitlegacy/#podcast)
# tags fixed; the rest are LLM-chosen for relevance.

HASHTAG_SELECTION_V1 = """Generate platform-optimized hashtags for a short-form video.

Video title: {title}
Hook: {hook}
Topics: {topics}
Content excerpt:
\"\"\"
{extracted_text}
\"\"\"

REQUIREMENTS:
- Return 8-10 hashtags (we'll add 5 fixed ones for a 13-15 total).
- All lowercase, no spaces, no special chars beyond letters/numbers.
- Specific to THIS clip's content, not generic gaming.
- Mix of: niche-specific (e.g., #soulslike if discussing soulsborne), platform-specific
  (e.g., #ps5 if PS5 mentioned), broad-discoverability (e.g., #gamingnews if news).
- Don't include any of these (we add them automatically):
  #fyp, #foryoupage, #explorepage, #shorts, #8bitlegacy, #podcast,
  #retrogaming, #retrogames, #videogames, #gaming, #nintendo, #playstation
- Avoid spammy/banned hashtags or anything off-brand.

Return STRICT JSON only:
{{
  "hashtags": ["#tag1", "#tag2", ...],
  "reason": "why these tags fit the clip"
}}
"""


# =====================================================================
# AUDIO MIX MOOD CLASSIFIER (post-pick, text only)
# =====================================================================
# Classifies clip mood so render_clip.py can pick the appropriate
# dialog-to-music ratio. Currently fixed at 0.12 — this lets it adapt.

AUDIO_MIX_MOOD_V1 = """Classify the mood of this clip so we can mix audio appropriately.

Title: {title}
Content excerpt:
\"\"\"
{extracted_text}
\"\"\"

Categorize the clip's emotional energy:

- **intense**: heated debate, passionate argument, controversial hot take.
  → Music should be quiet (0.08) so dialogue cuts through clearly.

- **storytelling**: personal anecdote, narrative, recollection.
  → Music slightly under (0.10) so attention stays on the story.

- **casual**: lighter chat, banter, joking, relaxed conversation.
  → Music can be normal (0.12).

- **upbeat**: hype, excitement, anticipation, positive energy.
  → Music can be louder (0.14) to amplify energy.

Pick ONE category. If borderline, pick the LOWER-energy option (safer for clarity).

Return STRICT JSON only:
{{
  "mood": "intense" | "storytelling" | "casual" | "upbeat",
  "music_volume": 0.08 | 0.10 | 0.12 | 0.14,
  "reason": "one-sentence summary"
}}
"""


# =====================================================================
# MUSIC BED MOOD-MATCHING (used at music-bed catalog build time, OR per-clip)
# =====================================================================
# When building the music-bed catalog: per-bed mood classification.
# When picking music per-clip: we use clip mood + bed catalog to find the best match.

MUSIC_BED_MOOD_CLASSIFY_V1 = """You're classifying a music bed (instrumental track) for use under
a podcast clip. Based on the filename/title metadata only (you can't hear it),
infer the LIKELY mood and energy.

Filename: {filename}
Source/origin (if known): {source}

Pick ONE primary mood and ONE energy level:

Moods: intense | dramatic | reflective | nostalgic | upbeat | playful | epic | chill | mysterious | unknown
Energy: low | medium | high | unknown

If the filename gives no useful info (e.g., "track_03.mp3"), return mood=unknown.

Also: is this likely PODCAST-APPROPRIATE? (Some music beds — vocal-heavy, dialogue-conflicting,
explicit, brand-mismatched — shouldn't go under our podcast clips.)

Return STRICT JSON only:
{{
  "mood": "intense" | "dramatic" | "reflective" | "nostalgic" | "upbeat" | "playful" | "epic" | "chill" | "mysterious" | "unknown",
  "energy": "low" | "medium" | "high" | "unknown",
  "podcast_appropriate": <bool>,
  "reason": "one-sentence justification"
}}
"""


# =====================================================================
# GATE 4 — Final comprehensive approval (multimodal Opus)
# =====================================================================

GATE_4_FINAL_APPROVAL_V1 = """You are the FINAL QA reviewer before this short ships to followers.
Your decision determines whether this clip publishes.

You receive:
  - 6 keyframes from across the clip (every ~15% of duration)
  - The clip's title, hook, and topics
  - The transcript text the viewer will hear
  - Scene detection + crop data
  - Word-timing first 30 words

CLIP CONTEXT:
  Title: {title}
  Hook: {hook}
  Topics: {topics}
  Duration: {duration_sec:.1f}s
  Scene boundaries: {scenes_summary}

EXTRACTED TEXT (audio + captions):
\"\"\"
{extracted_text}
\"\"\"

WORD TIMINGS (first 30 words):
{word_timings_excerpt}

CONTEXT: This is podcast content for TikTok / Reels / YT Shorts. The pipeline
must produce DOZENS of shippable clips per episode. Your job is to catch
ACTUALLY BROKEN content — not perfectionist filtering. Conversational tangents,
imperfect hooks, and minor narrative wobbles are FINE for podcast shorts —
that's what podcasts sound like. Reject only on hard-broken content.

SCORE ON 5 DIMENSIONS:

1. **NARRATIVE** (does it make sense alone?):
   - Comprehensible to a viewer with no podcast context? (→ acceptable+)
   - Tangents are FINE if the clip eventually lands somewhere or has self-contained value
   - "critical_fail" only if: gibberish, mid-thought start AND mid-thought end with no payoff,
     or the clip is impossible to follow without prior episodes

2. **VISUAL** (looking at the 6 frames):
   - Speaker visible in most frames? (one off-center frame is acceptable)
   - "critical_fail" only if: speaker is OFF-FRAME (head cropped out) in 2+ keyframes,
     OR a scene transition causes the wrong person to be on-screen for an extended period

3. **AUDIO** (inferred from frames + word timings):
   - Captions roughly match dialogue?
   - "critical_fail" only if: captions are CLEARLY wrong (talking about different topic
     than the on-screen text), OR text in keyframes is nonsensical word salad

4. **ENGAGEMENT** (algorithmic-feed test):
   - Has SOMETHING in the first 10 seconds that could hold attention (opinion, fact,
     story setup, curiosity, banter)?
   - "critical_fail" only if: first 10 seconds is pure filler ("yeah uh so anyway, like I
     was saying before, you know, it's kind of like..."), no content of any kind

5. **TITLE MATCH**:
   - Title accurately describes the clip's primary subject? (Some tangent is OK)
   - "critical_fail" only if: title says X, content is mostly Y (the Black Flag / Resident
     Evil mismatch you saw before — title and content about completely different things)

DECISION RULES (CALIBRATED 2026-05-08 for "ship dozens, reject only broken"):
- Default → APPROVE
- 1-2 dimensions "concerning" with NO critical_fail → APPROVE (it's good enough for
  podcast shorts)
- ANY dimension is "critical_fail" → REJECT
- If you'd describe it as "borderline but probably fine" → APPROVE not FLAG. FLAG is
  reserved for "I genuinely can't tell — needs a human eye"
- When in doubt → APPROVE. The user can delete a single bad post; missing a whole episode's
  worth of content because of perfectionism is the worse failure mode.

Return STRICT JSON only:
{{
  "scores": {{
    "narrative": "critical_fail" | "concerning" | "acceptable" | "good" | "excellent",
    "visual": "critical_fail" | "concerning" | "acceptable" | "good" | "excellent",
    "audio": "critical_fail" | "concerning" | "acceptable" | "good" | "excellent",
    "engagement": "critical_fail" | "concerning" | "acceptable" | "good" | "excellent",
    "title_match": "critical_fail" | "concerning" | "acceptable" | "good" | "excellent"
  }},
  "issues": [
    {{
      "category": "narrative" | "visual" | "audio" | "engagement" | "title_match",
      "severity": "critical" | "major" | "minor",
      "issue": "description",
      "recommendation": "reject" | "flag_for_manual" | "acceptable"
    }}, ...
  ],
  "final_decision": "APPROVE" | "FLAG_FOR_REVIEW" | "REJECT",
  "reason": "one-sentence summary suitable for a Navi task"
}}
"""
