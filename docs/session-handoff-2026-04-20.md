# Session Handoff — 2026-04-20 (EOD)

**Session length:** ~8 hours (start ~8:12 AM through ~4:33 PM EDT, Mac office)
**Resume:** tomorrow — start here, then check the cowork handoff at `docs/cowork-session-2026-04-20-ads-launch.md` if cowork finished while we were off.

---

## TL;DR

- Full content-automation pipeline (podcast → shorts → socials) is BUILT and DEPLOYED to a new `8bit-pipeline` Docker container on TrueNAS. Watcher + buffer scheduler + Navi alerting all live. Idle until you drop content into `/mnt/pool/NAS/Media/8-Bit Legacy/*/incoming/`.
- Google Ads launch is MID-FLIGHT. Research + bidding math + safety + cowork brief all done. Cowork is currently executing Tasks 2-6 of the ads launch brief (Task 1 deferred — Web vs Desktop OAuth client mismatch blocker).
- Three cowork cycles ran today: Zernio (DONE), Google OAuth for YouTube (DONE), Ads launch (IN PROGRESS at handoff).
- Memory massively expanded — 6 new reference/feedback files ensure future sessions don't re-discover what we figured out today.

---

## Where things stand right now (end of day)

### 🟢 Fully done + live

| System | State |
|--------|-------|
| **Zernio social scheduler** | Account + API key + 4 platforms connected (IG `@8bitlegacyretro`, FB `@8bitlegacyco`, TikTok `@8bitlegacy.com`, YT `8-Bit Legacy`). Smoke-test green. |
| **YouTube OAuth** | `oauth2client.json` live at `/mnt/pool/apps/8bit-pipeline/config/` on TrueNAS. First podcast upload will trigger 30-sec browser auth dance. |
| **TrueNAS pipeline container** | `8bit-pipeline:latest` built + running. Polling `/media/podcast/incoming/` and `/media/photos/incoming/` every 5 min. Buffer scheduler runs every ~60 min. Emits Navi tasks on failure. |
| **NAS drop folder tree** | `/mnt/pool/NAS/Media/8-Bit Legacy/` with `podcast/{incoming,processing,archive,clips-archive,music-beds}`, `photos/{incoming,processing,archive}`, `state/`, `logs/`. DROP-HERE-README.md in place. |
| **Navi alerting** | `scripts/navi_alerts.py` emits tasks in the correct {text, type, done, dueDate} shape. Bug fixed + hot-patched + rebuilt into container. Two smoke-test tasks visible in your Core list. |
| **Shorts pipeline quality bar** | `pick_clips.py` rewritten — stand-alone clips only, 60-90s target, sentence-boundary snap, rescue logic, stand-alone + quality scoring. Validator unit-tested. |
| **Shorts captions** | Hashtags-only, 15-tag cap (YT Shorts safe). `#fyp #foryoupage #explorepage` + retro/gaming base + 3 topic tags. |
| **Photo captions** | 5-entry rotation of generic "store is alive" copy, IG + FB only. No Claude API calls anymore. |
| **YT metadata generator** | `generate_metadata.py` rewritten with 8-Bit Podcast house style (pipe separator, hot-take framing, ALL CAPS emphasis) + chapter timestamps for full eps + YT-algorithm-optimized tags. |
| **Memory** | 6 new files: reference_infrastructure, reference_navi_task_api, reference_youtube_style, feedback_dashboard_scope, feedback_shorts_quality, feedback_ads_strategy. Every future session opens with this context. |

### 🟡 In flight at handoff

| Workstream | State |
|------------|-------|
| **Cowork ads launch** | Tasks 2-6 in-progress (MC diagnostics, conversion tracking verify, campaign rename+subdivide+bids, negatives import, CIB feed upload, Winners landing page spot-checks). Task 1 (OAuth refresh) deferred to a future cowork cycle. |

### 🔴 Explicitly deferred (resume tomorrow or later)

| Task | Reason deferred |
|------|-----------------|
| **Google Ads OAuth refresh (cowork Task 1)** | Web-type OAuth client can't use `oob` redirect anymore. Plan: create Desktop OAuth client in same GCP project, swap creds, re-run flow. Full recipe in `docs/claude-cowork-brief-2026-04-20-ads-launch.md` Task 1 section. Paused by user — cowork capacity prioritized for Tasks 2-6. |
| **Dashboard redeploy to VPS with new safety.ts** | Main session needs VPS access. Not set up. Until redeploy: old safety rules ($25 daily cap, 3-day × $10 no-conv) are what the VPS scheduler actually enforces. New rules ($40 cap, $50 lifetime no-conv) exist in the repo but aren't live. |

---

## What shipped today (15 commits, all local)

Commit range: `595ead0` → `9c36a8b`. None pushed yet — **pushing this handoff doc + all prior commits together.**

| # | Commit | What |
|---|--------|------|
| 1 | `595ead0` | Shorts hashtags-only captions; photos generic rotation (removed Claude caption gen) |
| 2 | `19cfa1d` | `scripts/navi_alerts.py` — emit tasks to Navi Core |
| 3 | `e69ca58` | `pick_clips.py` rewritten for stand-alone quality |
| 4 | `9669dca` | `scripts/watcher/drop_watcher.py` — NAS polling loop |
| 5 | `7cbdae5` | drop_watcher: fix rendered-clips path + invoke buffer scheduler periodically |
| 6 | `6fd5ebb` | `scripts/watcher/buffer_scheduler.py` — archive re-post when queue runs low |
| 7 | `b4a66db` | `deploy/` — Dockerfile + compose + tar-based TrueNAS deploy script + DEPLOY.md |
| 8 | `d4727e7` | Rewrite `generate_metadata.py` — YT-algorithm + channel style mirror |
| 9 | `09a1689` | Cowork brief — Google OAuth for YouTube uploads |
| 10 | `f5fdbe9` | Cowork handoff 2026-04-20: Google OAuth for YouTube uploads complete |
| 11 | `67b6419` | navi_alerts: fix task field shape — use {text, type, done, dueDate} |
| 12 | `46a7ad4` | Ads launch research + CIB exclusion + safety.ts patch + cowork brief |
| 13 | `8310a25` | Bump daily budget $17 → $20 (confirmed); skip test purchase |
| 14 | `d79b425` | Fix budget preflight line math |
| 15 | `9c36a8b` | Defer Task 1 (OAuth refresh) in cowork brief — Web-client oob blocker |

---

## Files of note (for tomorrow's re-orientation)

**Read first tomorrow:**
1. `docs/session-handoff-2026-04-20.md` — THIS file
2. `docs/cowork-session-2026-04-20-ads-launch.md` — if cowork wrote one while we were off
3. `docs/ads-launch-research-2026-04-20.md` — the ads strategy + go/no-go decision tree

**Reference as needed:**
- `docs/claude-cowork-brief-2026-04-20-ads-launch.md` — what cowork is executing + resume plan for Task 1
- `deploy/DEPLOY.md` — how the pipeline container is deployed + troubleshooting
- `scripts/navi_alerts.py` + `reference_navi_task_api.md` — task emission contract (DO NOT use `title`, must use `text`)

---

## FULL NEXT STEPS (in execution order for tomorrow)

### Step 1 — Check cowork's handoff (5 min)

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only  # pick up any commits cowork may have made
ls docs/cowork-session-2026-04-20-ads-launch.md
```

If the cowork handoff exists, read it. Look for:
- Which of Tasks 2-6 went GREEN / BLOCKED
- Merchant Center diagnostics state (any disapprovals > 50? any account-level issues?)
- Conversion tracking "Recording" state (all 4 primary goals? Purchase showing `Created`?)
- Whether CIB supplemental feed uploaded successfully
- Winners landing page spot-checks (any broken?)
- Cowork's go/no-go recommendation

### Step 2 — Resume Task 1 (OAuth refresh via Desktop client) (~15 min)

**Only if cowork capacity available.** Per the deferred-task notes in `docs/claude-cowork-brief-2026-04-20-ads-launch.md`:

1. Tristan (or cowork): GCP Console → find the project owning client_id prefix `585154028800-30b12ji9qdncj1ng4lv8f8i3atnafce9`
2. Same project → APIs & Services → Credentials → **Create Credentials → OAuth Client ID → Desktop app** → name `8bit-legacy-ads-desktop`
3. Copy new client_id + client_secret
4. Main session (me) updates `config/.env` + `dashboard/.env.local` with new creds
5. Visit auth URL with new Desktop client_id → grant AdWords scope → copy auth code
6. Main session exchanges code for refresh_token, writes to both env files
7. Test with a live GAQL query to verify API access restored

**Once this works:** main session can directly pull campaign stats, optimize bids as data rolls in, tune negatives programmatically.

### Step 3 — Verify CIB supplemental feed propagation (once 24-48h have elapsed from cowork's upload)

1. Log into Merchant Center → Products → All products
2. Filter by `Disapproved for: Shopping ads`
3. Search for any CIB variant (title contains "Complete" or "CIB")
4. Confirm shows `Disapproved for Shopping_ads` + `Active for Free_listings`
5. If 0 matches: format mismatch. Regenerate CSV with correct format, re-upload.

**Critical: DO NOT enable the ads campaign until this propagation is verified.** If CIB variants are still eligible, first-day ad clicks may route to high-price CIB offers instead of competitive Game Only.

### Step 4 — Redeploy dashboard to VPS with new safety.ts (pending VPS access arrangement)

Patched file: `dashboard/src/lib/safety.ts` adds:
- `MAX_DAILY_AD_SPEND: 25 → 40` (accommodates $20/day × 2 Google overspend)
- `LIFETIME_NO_CONVERSION_CEILING: 50` (hard pause at $50 cumulative with 0 conv)
- New Check 2A: lifetime cumulative trip (primary)
- Check 2B: 3-day consecutive (kept as defense-in-depth)

**Until this is live on the VPS, automated $50 trip DOES NOT fire.** The VPS scheduler runs the old safety.ts. Either:
- Grant main session VPS SSH access → I redeploy
- User redeploys manually (dashboard has a build/deploy flow of its own)
- Skip and rely on manual monitoring + Google Ads UI pause

### Step 5 — Final pre-launch gate (once steps 1-4 green)

Re-read `docs/ads-launch-research-2026-04-20.md` Part 5 blockers. All 5 must be green:
- [ ] OAuth refresh done (step 2)
- [ ] MC diagnostics clean (cowork task 2, verified in their handoff)
- [ ] Conversion tracking all 4 goals Recording or "No recent conversions" (cowork task 3)
- [ ] CIB supplemental feed propagated (step 3)
- [ ] Safety.ts live on VPS (step 4)

Then Tristan flips campaign from Paused → Enabled in Google Ads UI.

### Step 6 — Day 1 monitoring (first 24h after enable)

Per `docs/ads-launch-research-2026-04-20.md` Part 6:
- Check spend every 6h (target ~$20/day; $0 = issue, $40+ = anomaly)
- Impressions (500-2000 on day 1 is normal)
- CTR > 0.5% baseline for Shopping ads
- Read top 20 search terms in the report — add junk to negatives aggressively in first week
- Any Navi tasks from the dashboard's ads-safety-check? Investigate immediately.

---

## Sidetracks (not blocking ads launch)

- **First real pipeline test** — when home with NAS-Finder access, drop a photo batch or podcast episode
- **Music bed library** — drop retro OSTs into `podcast/music-beds/`, run `prepare_music.py` once (one-time)
- **Phase 2 — VPS scheduler jobs → Navi alerts** — retrofit the 5 VPS scheduled jobs to emit Navi tasks on failure (low priority)
- **Linux desktop `.env` sync** — when home, add `ZERNIO_API_KEY`, `ANTHROPIC_API_KEY` to `config/.env` on Linux for local dev
- **YT Shopping** — gated at 1,000 subscribers
- **Thumbnail automation (DTR)** — `generate_thumbnail.py` already renders a basic fallback; full automation later

---

## Known issues / gotchas flagged during session

1. **CIB supplemental feed format is my best guess** (`shopify_US_{prodNum}_{varNum}`) — cowork brief instructs verification against MC before relying on it
2. **Google Ads OAuth in Testing mode** expires every 7 days — expect a weekly Navi task to re-auth until we publish the OAuth app to Production (multi-week Google verification)
3. **Pokemon games inclusion** — user explicitly wants games IN ads, cards OUT. Filter is by `category:pokemon_card` tag. If any Pokemon game is mis-tagged with that, it would be wrongly excluded. Spot-check via Merchant Center after feed processes.
4. **Daily spend safety at old $25** — until dashboard redeployed, Google's 2x overspend at $20 base could false-trip the safety. Acceptable trade-off, but know it could happen.

---

## First action tomorrow (single crisp directive)

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
cat docs/cowork-session-2026-04-20-ads-launch.md  # if exists
cat docs/session-handoff-2026-04-20.md            # this file — re-orientation
```

Then pick up from "Step 1 — Check cowork's handoff" above.

---

## Git state at handoff

15 commits ahead of origin. Pushing this handoff + all prior commits in the same push. If push fails due to the `criticalmkt` gh-auth issue (seen earlier today), switching to `WhateverSkyler` via `gh auth switch -u WhateverSkyler` and pushing should work.
