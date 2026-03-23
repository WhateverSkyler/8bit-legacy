# The 8-Bit Legacy Podcast — Content Pipeline

## Overview
Record once (2hrs biweekly) → produce 1 full episode + 3-5 topic videos + 20-50 short clips.

---

## Recording Checklist (Your Part)

### Equipment
- 3x cameras (one per person)
- Audio interface + 3x mics (Shure/AT2020) → FL Studio (separate track per person)
- Good lighting (ring lights or softboxes)

### Before Recording
- [ ] Test all 3 cameras (framing, focus, white balance matched)
- [ ] Test all 3 mics in FL Studio (levels, no clipping)
- [ ] Have a loose topic list (5-7 talking points for 2hrs)
- [ ] Record a 5-second clap on camera for audio sync reference

### During Recording
- FL Studio: record all 3 mic tracks simultaneously
- Cameras: all 3 rolling continuously
- Natural conversation — don't worry about "segments", the AI editing handles cuts

### After Recording — Export & Handoff
1. **FL Studio**: Export each mic as a separate WAV (48kHz/24bit):
   - `person1_audio.wav`
   - `person2_audio.wav`
   - `person3_audio.wav`
2. **Cameras**: Copy video files, rename clearly:
   - `person1_video.mp4`
   - `person2_video.mp4`
   - `person3_video.mp4`
3. **Drop all 6 files** into: `~/Podcast/Episodes/EP[XX]-[date]/raw/`

---

## Editing Pipeline (AI-Assisted)

### Step 1: Full Episode Edit — AutoPod ($29/mo)

**Setup (one-time):**
1. Install DaVinci Resolve (free) or Premiere Pro
2. Install AutoPod plugin ($29/mo, 30-day free trial)
3. Create a project template with:
   - Intro bumper (5-10 sec branded animation)
   - Outro card (subscribe + website URL)
   - Lower thirds for each person's name
   - 8-Bit Legacy logo watermark (corner)

**Per-episode workflow (~30 min hands-on):**
1. Open DaVinci Resolve → import all 6 files
2. Sync audio to video (DaVinci has auto-sync, or use the clap)
3. Run AutoPod:
   - Set camera assignments (person 1 = cam 1, etc.)
   - AutoPod analyzes audio → switches to active speaker's camera
   - Adds wide shots during group reactions
4. **Insert the 8-Bit Legacy ad** (see below) at ~30min mark
5. Quick review: scrub through, fix any weird cuts (~10 min)
6. Add intro + outro
7. Export: 1080p or 4K for YouTube

**Upload to YouTube:**
- Title: "The 8-Bit Legacy Podcast — EP [XX]: [Topic]"
- Description: timestamps, links, social links
- Tags: retro gaming, podcast, 8-bit legacy, [topic tags]
- Schedule via YouTube Studio

### Step 2: Topic Videos (3-5 per episode)
From the 2hr episode, identify 3-5 standalone topic segments (10-20 min each):
1. In DaVinci Resolve: mark in/out points for each topic
2. Export each as a separate video
3. Add unique title card + thumbnail
4. Upload as standalone YouTube videos
5. Schedule 1-2/week between full episodes

### Step 3: Short-Form Clip Factory — OpusClip (free tier to start)

**Workflow (~15 min hands-on):**
1. Upload the finished full episode to OpusClip
2. OpusClip AI:
   - Identifies the most engaging 30-90 second moments
   - Auto-crops to vertical (9:16)
   - Adds animated captions
   - Scores each clip by virality potential
3. Review top 20-30 clips, discard any duds
4. **Add the 8-Bit Legacy banner overlay** to each clip (see below)
5. Schedule across platforms:
   - TikTok: 2-3/day
   - YouTube Shorts: 1-2/day
   - Instagram Reels: 1-2/day
6. Space out over 2 weeks until next episode

---

## Ad/Sponsor Inserts

### Mid-Roll Ad (1-2 min, inserted in full episodes + topic videos)

**Script template:**
```
[Quick transition/jingle — 3 sec]

"Quick shout-out to our sponsor — us! If you're watching this, you probably
love retro games as much as we do. 8-Bit Legacy is our online store where
you can grab classic games, consoles, and accessories at prices that won't
empty your wallet.

Every game is tested and quality-checked before it ships, and we're
consistently cheaper than the big retro game stores. Whether you're looking
for that childhood favorite or building out your collection, check us out
at 8bitlegacy.com — link in the description.

Now back to the show."

[Quick transition/jingle — 3 sec]
```

**Production:**
- Record this as a separate audio clip (re-record occasionally for freshness)
- Pair with a simple animated graphic:
  - 8-Bit Legacy logo
  - Website URL: 8bitlegacy.com
  - Quick montage of product screenshots / store preview
  - Retro pixel-art style animation
- **Duration:** 45-90 seconds
- **Placement:** ~30 min into full episodes, ~5 min into topic videos

### Short-Form Banner Overlay (for TikTok/Shorts/Reels)

**Design specs:**
- **Position:** Bottom of frame (above caption area) or top
- **Size:** ~15-20% of frame height, full width
- **Content:** "8bitlegacy.com" + small logo
- **Style:** Semi-transparent (60-70% opacity), retro pixel font
- **Color:** Match brand — could be retro green on black, or white on brand color
- **Duration:** Appears for last 5-10 seconds of each clip (not the whole time — non-intrusive)
- **Alternative:** Pinned comment on each post with store link

**Implementation:**
- Create as a PNG overlay in Canva/Photoshop
- OpusClip or CapCut can add overlays during export
- Or batch-apply with FFmpeg:
  ```bash
  ffmpeg -i clip.mp4 -i banner.png -filter_complex "overlay=0:H-h:enable='between(t,duration-8,duration)'" output.mp4
  ```

---

## Content Calendar (Per Episode Cycle = 2 weeks)

### Day 1 (Recording Day)
- Record 2hr podcast with the guys

### Day 2-3 (Post-Production)
- Edit full episode with AutoPod (~30 min)
- Upload full episode to YouTube (schedule for Day 4)
- Feed to OpusClip → generate clips
- Cut 3-5 topic videos

### Day 4 (Release Day)
- Full episode goes live on YouTube
- Post announcement on FB/IG/TikTok
- Start short-form clip schedule (2-3/day)

### Day 5-14 (Content Distribution)
- Short clips posting automatically via Buffer/OpusClip scheduler
- Topic videos releasing 1-2/week
- Regular product posts continuing on FB/IG (social-generator.py)

### Repeat every 2 weeks.

---

## Platforms & Scheduling

| Platform | Content Type | Tool | Cadence |
|----------|-------------|------|---------|
| YouTube | Full episodes | YouTube Studio | Biweekly |
| YouTube | Topic videos | YouTube Studio | 1-2/week |
| YouTube Shorts | Clips | Buffer/OpusClip | 1-2/day |
| TikTok | Clips | Buffer/OpusClip | 2-3/day |
| Instagram Reels | Clips | Buffer | 1-2/day |
| Instagram Feed | Product posts | Buffer | 3-4/week |
| Facebook | Product posts + clips | Buffer | 3-4/week |

---

## Tool Costs (Lean Stack)

| Tool | Cost | Notes |
|------|------|-------|
| DaVinci Resolve | FREE | Full editing suite |
| AutoPod | $29/mo | 30-day free trial, cancel when not recording |
| OpusClip | FREE | 60 credits/mo on free tier (enough for 1 episode) |
| Buffer | $0-18/mo | Free: 3 channels, 10 posts each |
| YouTube Studio | FREE | Upload + schedule |

**Total: $29-47/mo** (or $0 during free trial period)
