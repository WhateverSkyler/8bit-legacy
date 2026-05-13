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
# COLD-VIEWER OPENER TEST (text only, post-pick, pre-Gate-1)
# =====================================================================
# Catches the most common failure mode: clip starts mid-sentence or with
# a continuation word so a cold-scroll viewer has no idea what's being
# discussed. Gate 1 sees the WHOLE clip and can rationalize bad openings
# from later context. This gate sees ONLY the first 5 seconds, no
# title, no hook, nothing else — same as a real viewer who just paused.

COLD_OPENER_TEST_V1 = """You are deciding whether a short-form clip's opener works for a cold viewer (TikTok/Reels scroll, no prior context).

CURRENT CLIP START at {current_start_sec:.2f}s. The first 5 seconds the viewer would hear:

FIRST 5 SECONDS (current opener):
\"\"\"
{opener_text}
\"\"\"

CONTEXT — the 20 seconds of transcript SURROUNDING the current start, with absolute timestamps, so you can suggest a better start if needed:

\"\"\"
{context_window}
\"\"\"

EVALUATE THE CURRENT OPENER:

1. **Does the speaker introduce a clear topic?** Can a cold viewer, with zero prior knowledge, tell what subject is being discussed?
2. **Does the opening grammatically make sense as the START of someone talking?**
   Continuation words ("of", "to", "and", "but", "the", "for", "with", "in", "on", "or", "yeah", "right", "exactly", "anyway", "so") almost never start a stand-alone clip. Same with unintroduced pronouns (he/she/they/it/that).

EXAMPLES (current opener → judgment):
  - "Pokemon cards used to be fun for kids" → PASS (subject + complete thought)
  - "I'd rather support a local game store" → PASS (clear stance)
  - "Of like, kind of pre-scalping the cards" → BAD (starts on preposition)
  - "Yeah I totally agree, and that's why" → BAD (reactive, no subject)
  - "He was saying that they were going to" → BAD (unintroduced pronouns)
  - "On the road a lot, I wasn't a big fan of it" → BAD (mid-sentence)

DECISIONS:

- **PASS**: current opener is clean — both questions yes.

- **ADJUST**: current opener is bad BUT a clean opening exists within the surrounding 20s window. Use `suggested_start_sec` to point to the absolute timestamp where a CLEAN, complete-thought sentence begins. Pick the start time of the FIRST whole sentence in the window that:
    (a) introduces a clear subject (no unintroduced pronouns),
    (b) doesn't start on a continuation/filler word,
    (c) is on-topic with what the clip is about.
  Always prefer ADJUST over REJECT when any clean sentence exists within the window.

- **REJECT**: only when there is NO clean opening sentence anywhere in the 20s window — the entire region is mid-conversation fragments.

Return STRICT JSON ONLY (no prose, no markdown fences, start with `{{` end with `}}`):
{{
  "topic_clear": true | false,
  "grammatical_start": true | false,
  "recommendation": "PASS" | "ADJUST" | "REJECT",
  "suggested_start_sec": null | <absolute timestamp in seconds, from the context window>,
  "reason": "one short sentence explaining the call"
}}
"""


# =====================================================================
# GATE 1 — Narrative coherence re-validation (text only)
# =====================================================================

GATE_1_NARRATIVE_COHERENCE_V1 = """You are a stand-alone-ness auditor for short-form video clips.

A clip is being considered for publishing on TikTok / Reels / YouTube Shorts. **You
must judge this clip AS A COLD VIEWER would experience it** — someone scrolling
who has never heard the podcast and only sees what's IN the clip itself. They do
NOT see the title, do NOT see the hook, do NOT see the surrounding context.

Common failure mode: a clip starts with "I'm just impressed that THEY were able to
keep..." — title says "Donkey Kong Tropical Freeze" but the cold viewer doesn't
know who "they" refers to or what "level of difficulty" is being kept. The clip
relies on prior conversation the viewer never heard. **REJECT these.**

CLIP DURATION: {duration_sec:.1f}s
BOUNDARIES: {start_sec:.2f}s – {end_sec:.2f}s

EXTRACTED CLIP TEXT (THIS IS ALL THE COLD VIEWER GETS — judge from this alone):
\"\"\"
{extracted_text}
\"\"\"

⚠️ Title and hook are NOT shown to you on purpose. If the clip text doesn't make
sense WITHOUT them, it doesn't make sense to a cold viewer either. Reject.

For TIMING reference only (NOT for context inference) — surrounding transcript:
\"\"\"
{surrounding_context}
\"\"\"
USE THE SURROUNDING TEXT ONLY to verify whether the clip's opening pronouns
have antecedents IN THE PRIOR AUDIO (which the viewer never heard). If "they"
in the clip's first sentence refers to people introduced 30 seconds before the
clip starts → REJECT, because the cold viewer didn't hear that intro.

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

CONTEXT: this title gets used TWO ways for cold scrolling viewers:
  (a) as the post caption on TikTok / IG Reels / YT Shorts
  (b) as a TEXT OVERLAY rendered on the first 5 seconds of the video itself

So it MUST (1) immediately tell a stranger what the clip is about, (2) sound
natural — like a human podcast editor wrote it, not a content-marketing AI —
and (3) fit cleanly as a 1-2 line overlay (~24 chars per line).

Score on 5 dimensions:

1. **Specific not vague AND captures the MAIN POINT**: Title names the
   actual subject AND the actual thesis the speakers are making. The
   title must be the answer to "what is this clip ABOUT" — not just
   any noun mentioned in passing.
   - PASSES: "Scalpers Are Ruining Kids' Hobby" (when the clip's main
     argument is that scalpers ruin trading card collecting for kids)
   - FAILS: "GameStop Pro Doubles The Card Limit" for that SAME clip —
     the doubled limit is a passing FACT used as evidence; the actual
     POINT is about scalpers + kids.
   - FAILS: "An interesting take on retro" (vague, nothing specific)
   If the title focuses on a tangential concrete fact while ignoring
   the clip's argument, REWRITE or REJECT.

2. **Natural / not corny**: Sounds like a real podcast editor wrote it.
   AVOID:
   - Sentence fragments cut mid-phrase ("Yoshi and Kirby Got Too Easy — But Donke")
   - Forced punchlines / marketing-speak ("The Truth About...", "Why X Will Shock You")
   - Made-up jargon that isn't in the clip ("Pre-Scalping Trading Cards")
   - Random capitalization ("XBOX is BETTER Than PS5 PRO")
   - Awkward em-dash compounds that don't read cleanly
   PREFER short declarative sentences or short questions, written how people
   actually talk. "Nintendo Made Their Games Too Easy" is natural. "DK Tropical
   Freeze: 2D Platforming PEAKED" is corny.

3. **Concise**: 4-8 words ideal, 4-10 hard max. <4 is usually too vague.
   >10 won't fit the overlay cleanly.

4. **Not clickbait**: No "you won't believe", "this changes everything",
   excessive ALL CAPS, fake questions, or promises the content doesn't deliver.

5. **Accurate**: Describes what's actually said. NOT a reframing or stretch.
   When in doubt, prefer the broader honest framing over a too-narrow one that
   misrepresents the whole.

   STRICT GROUNDING RULE: every CONTENT verb and noun in the title must
   appear in the extracted clip text — verbatim or as a clear, immediate
   paraphrase that a reasonable listener would agree captures the same
   point. If the title introduces a CONCEPT the speaker didn't actually
   discuss, score `accurate` as FAIL.

   Examples of grounded vs ungrounded titles for the SAME clip
   (speaker said "the puzzles aren't engaging and the world feels empty"):
     ✓ "Tears of the Kingdom Isn't Engaging"       — paraphrases "aren't engaging"
     ✓ "Tears of the Kingdom Feels Empty"          — direct quote
     ✗ "Tears of the Kingdom Is Too Easy to Break" — speaker never said "break" or
                                                     anything about breaking the game
     ✗ "Tears of the Kingdom Is Broken"            — invents a concept the speaker
                                                     didn't claim
   The ✗ titles introduce a "broken / breaking" frame that isn't in the
   transcript. Even though they "sound like a hot take," they're inaccurate
   and must REJECT (don't REWRITE — there's nothing in the source to
   support a corrected version, just remove this title from contention).

   Common offenders to watch for:
   - Metaphorical extensions ("ruins / breaks / kills / destroys / saves") that
     aren't actually in the clip
   - Hot-take framing the speaker didn't actually voice
   - Numerical claims (years, prices, percentages) not stated in the clip
   - Comparisons ("better than X", "worse than Y") the speaker didn't make

If you REWRITE, the new title MUST follow ALL FIVE rules above. Don't fix
clickbait by introducing corny phrasing. Don't fix vagueness by stuffing in
proper nouns that aren't central.

GOOD examples:
  "Nintendo Should Make Harder Games Again"
  "Why GameStop Wants to Buy eBay"
  "Xbox Is Becoming a Brand, Not a Console"
  "Ocarina of Time Still Needs a Remake"
  "Switch 2 at $450 Is Actually Competitive"

BAD examples (and why):
  "Yoshi and Kirby Got Too Easy — But Donke" (cut mid-word, corny em-dash)
  "GameStop Is Pre-Scalping Trading Cards" (made-up jargon "pre-scalping")
  "The Truth About Retro Gaming Today" (clickbait-flavored, vague)
  "Why XBOX Series X is BETTER Than PS5 PRO" (excessive caps, fake comparison)
  "GameStop Is Reportedly Bidding to Acquir" (cut mid-word)

DECISIONS:
- All 5 dimensions PASS → APPROVE
- 1 dimension borderline → APPROVE_WITH_NOTE
- ≥1 dimension fails clearly → REWRITE (return a better title)
- Cannot rewrite without misrepresenting the content → REJECT
- `accurate` scored FAIL because the title introduces an ungrounded concept
  → REJECT (do NOT REWRITE — the original title's premise isn't in the
  clip, so there's no honest rewrite available)

Return STRICT JSON only:
{{
  "scores": {{
    "specific": "good" | "borderline" | "fail",
    "natural": "good" | "borderline" | "fail",
    "concise": "good" | "borderline" | "fail",
    "not_clickbait": "good" | "borderline" | "fail",
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
