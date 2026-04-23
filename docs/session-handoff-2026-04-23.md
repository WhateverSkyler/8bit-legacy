# Session Handoff — 2026-04-23 EOD

**Resume target:** tomorrow (2026-04-24).
**Previous:** `docs/session-handoff-2026-04-22.md`

---

## TL;DR

1. **Podcast shorts pipeline** got a big iteration today: face-centered crop, bigger captions, tuned duration policy, quieter music. **Had one regression mid-day** (face detection broke multi-camera clips → bad 1pm post you manually deleted), fixed with a conservative spread+offset gate on the override. Current queue is 7 fresh clips with the safe fallback center crop, next post 2026-04-23 19:00 ET.
2. **Ads campaign `8BL-Shopping-Games`** is still PAUSED, 18/18 preflight passing. Two soft gates remain before flip: (a) revert free shipping $35 → $50, (b) place a $5-10 real test order to flip Purchase conversion from Active/No-recent → Recording. Cowork brief is written + ready to paste.
3. **Commits pushed locally (local `main`, origin push blocked by known criticalmkt auth issue):**
   - `806e59c` Podcast shorts: face-crop + bigger captions + completion-rate duration
   - `c8678af` Ads launch: final gates brief, launch log, deprecate Winners-list docs
   - `7af75d0` render_clip: conservative face crop + quieter music bed

---

## Podcast pipeline — what shipped + current state

### Changes deployed to TrueNAS 8bit-pipeline container

| Change | File | Effect |
|---|---|---|
| Face-detect crop with multi-camera guard | `scripts/podcast/render_clip.py` | Override default center crop ONLY when (a) face X-spread across sampled frames < 200 px AND (b) median face > 220 px off-center. Otherwise keep the fixed center crop that was working pre-face-detection. Safe by default. |
| Caption font bump | `scripts/podcast/render_clip.py` | 70pt → 96pt, outline 5 → 7, marginV 240 → 260. Readable on phones. |
| Duration policy | `scripts/podcast/pick_clips.py` | Floor 30s · sweet spot 45-65s · ceiling 85s. Biased toward completion rate over length. Applies to future episodes only. |
| Music bed | `scripts/podcast/render_clip.py` | Volume 0.15 → 0.12 (~2 dB cut) per user "5% quieter". Tunable. |
| OpenCV dep | `deploy/requirements-pipeline.txt` | Added `opencv-python-headless>=4.10,<5` |
| Deploy-script bug fix | `deploy/deploy-to-truenas.sh` | Was silently excluding `assets/fonts/` from tarball — broke the Dockerfile's BebasNeue COPY step. Fixed. |
| Past-slot guard in scheduler | `scripts/podcast/schedule_shorts.py` | `_build_schedule(skip_past=True)` skips slots already in the past so mid-day rescheduling auto-lands on the next future slot. |

### Episode April 14 2026 queue state

**Published (leave alone):**
- 2026-04-23 09:00 ET — `c1` of topic 03 (original old-crop render)
- 2026-04-23 13:00 ET — `c2` of topic 03 (bad face-detection render, user manually deleted from TikTok/YouTube/Instagram)

**Queued (fresh re-renders, all use safe center crop):**
| When (ET) | Clip | Title |
|---|---|---|
| 2026-04-23 19:00 | 03-c3 | Why the Zelda Director Actually Gives Us Hope |
| 2026-04-24 09:00 | 05-c1 | Everything Metroid Prime 4 Added Was Bad |
| 2026-04-24 13:00 | 05-c2 | PS5 Pro Runs Cyberpunk at 60fps With Full Ray Tracing |
| 2026-04-24 19:00 | 05-c3 | Do Not Spend $900 on the PS5 Pro |
| 2026-04-25 09:00 | 05-c4 | Buying an Xbox in 2026 Is a Mistake |
| 2026-04-25 13:00 | FULL-c1 | Adult Gamers Cant Sit Still Anymore |
| 2026-04-25 19:00 | FULL-c2 | Handheld Gaming Is the Adult Gamer Fix |

All 7 go to TikTok + YouTube Shorts + Instagram Reels. Media URLs prefixed `1776965*` in Zernio (confirm via API if you want).

### Lessons learned (for future episode runs)

- The podcast is multi-camera cutting between 3 angles. A single fixed crop offset per clip cannot satisfy all cameras simultaneously unless the shot is actually single-camera.
- The face-detection guard (200 px spread threshold) will correctly identify multi-camera clips and default to center. It WILL kick in the face-centered override if a future clip is genuinely single-camera with a far-off-center subject — which was the original user complaint on the arcade-machine shot. Haven't seen such a clip yet in Episode 14; the audit log of today's re-render shows all 9 hit the multi-camera fallback.
- If the multi-camera center crop ever drifts off for a specific camera (e.g., arcade shot again), the right next-step is per-scene detection (PySceneDetect or similar) — detect camera cuts inside a clip and pick a crop based on which camera dominates. Not built yet; not needed for the current state.

---

## Ads campaign — where it stands

**Campaign:** `8BL-Shopping-Games` (ID 23766662629). **PAUSED.**

### Automated state — 18/18 pass
Run `python3 scripts/ads_preflight_check.py` anytime. All structural checks green: budget $20/day, listing tree correct, 334 negatives imported, networks scoped to Search, US geo, MC linked, 7 conversion actions enabled+primary, landing pages reachable.

### Conversion tracking state (as of 2026-04-23 ~11 AM)
- Purchase: **Active** · No recent conversions (flips to Recording on first real purchase)
- Add to cart: **Active** · No recent conversions
- Begin checkout: **Active** · No recent conversions
- Page view goal: Needs attention (soft warning — not a hard block per prior audit `docs/ads-conversion-tracking-status-2026-04-16.md`)

### Order + sourceability check (today)
- 180-day order history: **5 orders, 100% fulfillment rate on non-refunded**, 2 refunds were stale-pricing failures (root cause fixed 2026-04-15 per `docs/session-handoff-2026-04-15.md`), 1 paid order in transit as of Apr 18 is fine.
- Live eBay Browse API spot-check on 25 over_50 games: **18 green / 5 thin / 2 no-match** (the 2 no-matches are cosmetic — "X-men Wolveri - NES Game Rage - Gameboy Color Game" has a corrupted feed title, "WWF Raw - Sega 32X Game" is ultra-niche).
- Critically: **Mystical Ninja N64** (previously refunded) and **Aidyn Chronicles N64** (previously refunded) both came back with 15 active listings each at prices WELL below our 65% cost ceiling. The previous refunds were a timing fluke on stale pricing, not a structural sourcing problem. Full audit persisted at `/tmp/sourceability-audit.json` but not committed (throwaway).

### Honest launch probability (conservative)
- P(positive/breakeven ROAS in 30d): **35-45%**
- P(useful learning regardless of ROAS): **85%**
- P(account re-suspension from refund/chargeback spike): **10-15%**

**Verdict: +EV to launch.** The $700 promo credit covers the experiment. Worst case = $50 hard kill on the lifetime-no-conv ceiling, telling us CVR is broken on a cold store.

### Tomorrow's pickup plan (3 steps, ~15 min real work)

**Step 1 — Cowork executes the final gates brief:** `docs/claude-cowork-brief-2026-04-23-final-gates.md`

Copy-paste this into Claude Desktop cowork:

```
You are resuming work on the 8-Bit Legacy repo at github.com/WhateverSkyler/8bit-legacy. Pull latest before starting.

Execute the brief at docs/claude-cowork-brief-2026-04-23-final-gates.md end-to-end. Read it in full first. Two tasks, both browser-only:

1. Shopify admin → Settings → Shipping and delivery → flip the free shipping threshold back from $35 to $50 (and flat-rate max from $34.99 to $49.99). Verify via incognito checkout.

2. Place a $5-10 real test order end-to-end on 8bitlegacy.com (real card, real email, real address) so the Google Ads Purchase conversion fires end-to-end. Then refund it from Shopify admin and tag it "test-order".

Hard guardrails:
- DO NOT touch Google Ads (don't enable, don't edit bids/budget). Main session will flip the campaign via API after these are done.
- DO NOT modify anything else.
- STOP and report if anything unexpected.

When both are green, commit the handoff doc (docs/cowork-session-2026-04-23-final-gates.md) and tell Tristan in chat "both gates cleared — ready to flip."
```

**Step 2 — Verify in the chat:** cowork reports success. Optionally re-run `python3 scripts/ads_preflight_check.py` to confirm 18/18 still green.

**Step 3 — "Flip it":** tell me to enable the campaign. I'll:
1. Call the Ads API mutate endpoint on campaign 23766662629, status PAUSED → ENABLED
2. Record baseline timestamp + pre-launch state snapshot in `docs/launch-log.md`
3. Kick off the daily monitoring cadence via `scripts/ads_daily_report.py`

### Accepted residual risks (not blocking)

- **CIB exclusion supplemental feed** — Merchant Center Next UI refuses supplemental feeds on Merchant-API primary feeds. Auction optimizer favors cheaper Game Only variant naturally. Revisit after 14 days if CIB impression share > 20%.
- **VPS dashboard `safety.ts` redeploy** — new $40 daily cap + $50 lifetime no-conv ceiling are in the repo; VPS still runs old $25. Low risk for first week at $20/day base.
- **Page View "Needs attention"** — soft warning, per prior audit not a hard blocker.
- **2 products with feed/sourceability issues** — $94 + $51 list combined, <0.3% of the 802 over_50 universe. Will surface in daily report if they accumulate spend without converting. Cosmetic cleanup later.

---

## Commits to push (blocked by auth, need you)

Origin push is blocked by the known `criticalmkt` vs `WhateverSkyler` credential mismatch. Local main is 3 commits ahead of origin:

```
7af75d0  render_clip: conservative face crop + quieter music bed
c8678af  Ads launch: final gates brief, launch log, deprecate Winners-list docs
806e59c  Podcast shorts: face-centered crop + bigger captions + completion-rate duration
```

When you open a terminal: `cd ~/Projects/8bit-legacy && git push` (or whatever auth dance clears it).

---

## Outstanding from prior handoffs (unchanged today)

- **Audio podcast distribution** (Spotify/Apple) — pending host pick per `memory/project_audio_distribution.md`.
- **Homepage / trust-signal revamp** — tracked in `memory/project_website_revamp.md`; not launch-blocker.
- **VPS dashboard redeploy with new safety.ts** — listed above as accepted residual.

---

## Suggested first action tomorrow

```
cd ~/Projects/8bit-legacy && git pull --ff-only && git push  # clear the 3 local commits
cat docs/session-handoff-2026-04-23.md                        # re-orient
```

Then paste the Step 1 cowork prompt above, wait for cowork to report back, flip the campaign. Should be a short session.
