# Claude Cowork Brief — 2026-04-16 PM (Ads Campaign Launch)

**For:** Claude Code running on Tristan's Mac with browser access (Google Ads UI, Shopify admin, Google OAuth)
**From:** Claude Opus running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-16 12:10 PM EDT
**Goal:** Create the Google Shopping campaign and get it ready to enable. Everything else is built — this session is purely browser/UI work.

---

## Session start — mandatory

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

If pull fails, STOP and tell Tristan.

**Read these files:**
1. `CLAUDE.md` — project rules
2. `docs/google-ads-campaign-setup-guide.md` — THE GUIDE. This is the master doc for campaign construction.
3. This brief

---

## Context — what's already done

The laptop Claude built all the backend infrastructure:
- Dashboard upgraded: Campaign Health tab, Product Performance tab, Search Terms with bulk-negate
- Circuit breaker auto-trip conditions wired (daily spend, no conversions, store downtime, ROAS floor)
- 334 negative keywords formatted for import (`data/negative-keywords-google-ads-import.csv`)
- Campaign creation script exists (`scripts/create-shopping-campaign.py`) BUT the Google Ads API OAuth token is expired, so it can't run. **You need to do this in the browser.**
- Product description fix (30-day → 90-day returns) is running in background on all 7,600 products

The previous cowork session (this morning) confirmed:
- Merchant Center feed: 12,200 products healthy, 0 disapproved
- Customer Reviews program: enabled
- Conversion tracking: config is correct but events need re-firing (5 of 7 are Inactive)

---

## IMPORTANT: Campaign strategy has changed

The morning cowork session briefed Tristan on TWO campaigns (Winners + Discovery). **IGNORE THAT.** The plan changed after that session. We are building **ONE campaign:**

**Campaign: `8BL-Shopping-All`** — Standard Shopping, full product catalog, $14/day

The setup guide at `docs/google-ads-campaign-setup-guide.md` has every setting. Follow it exactly.

---

## Task 1 — Re-fire Conversion Tracking Events (5 min)

5 of 7 conversion actions are Inactive. They need a real event to fire.

1. Open https://8bitlegacy.com in an **incognito** window (no ad blockers)
2. Browse a product page (fires Page View + View Item)
3. Use the store search bar (fires Search)
4. Click Add to Cart on any product (fires Add to Cart)
5. Proceed to checkout — enter a real email and address (fires Begin Checkout)
6. Enter a real card, then **abandon** checkout (fires Add Payment Info)
7. Events take 2-4 hours to register in Google Ads. Move on to other tasks while waiting.

**For the Purchase event:** The only way to fire it is a real order. If Tristan wants, place a small order ($5-10 item) and refund it afterward. This is optional — the other 6 events are enough for launch.

---

## Task 2 — Re-authorize Google Ads API OAuth Token (10 min)

The OAuth2 refresh token in `dashboard/.env.local` is expired. This blocks the campaign creation script AND the dashboard monitoring. Fix it:

### Steps:
1. Open a browser and go to this URL (replace CLIENT_ID with the value from `dashboard/.env.local` → `GOOGLE_ADS_CLIENT_ID`):

```
https://accounts.google.com/o/oauth2/v2/auth?client_id=CLIENT_ID&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/adwords&access_type=offline&prompt=consent
```

2. Log in with the Google account that has access to Google Ads account `822-210-2291`
3. Grant permission when prompted
4. Google will show an authorization code — copy it
5. Exchange the code for a refresh token:

```bash
curl -s -X POST https://oauth2.googleapis.com/token \
  -d "code=PASTE_AUTH_CODE_HERE" \
  -d "client_id=CLIENT_ID_FROM_ENV" \
  -d "client_secret=CLIENT_SECRET_FROM_ENV" \
  -d "redirect_uri=urn:ietf:wg:oauth:2.0:oob" \
  -d "grant_type=authorization_code" | python3 -m json.tool
```

6. Copy the `refresh_token` value from the response
7. Update `dashboard/.env.local`:
```
GOOGLE_ADS_REFRESH_TOKEN=new_refresh_token_here
```
8. Also update `config/.env` if it has the same variable

### Verify:
```bash
python3 scripts/create-shopping-campaign.py --dry-run
```
If it prints "Authenticated successfully" instead of "Token has been expired", the token works.

---

## Task 3 — Create the Campaign (15 min)

**Option A (preferred): Use the script**
If Task 2 succeeded (OAuth token refreshed):

```bash
python3 scripts/create-shopping-campaign.py
```

This creates the campaign as PAUSED with:
- $14/day budget
- Manual CPC + Enhanced CPC
- Search network only
- US targeting
- 334 negative keywords auto-loaded

Then proceed to Task 4 for the product group subdivisions (can't be done via script).

**Option B (fallback): Build in Google Ads UI**
If the OAuth flow doesn't work, build the campaign manually following `docs/google-ads-campaign-setup-guide.md` Steps 1-5.

---

## Task 4 — Set Up Product Group Subdivisions (10 min, Google Ads UI)

This MUST be done in the Google Ads UI — the API is too complex for product group trees.

1. Go to Google Ads → Campaigns → `8BL-Shopping-All` → Ad group `all-products`
2. Click on **"All products"** in the product groups section
3. Click **Subdivide** → by **Custom label 2**
4. You'll see values like: `game`, `pokemon_card`, `console`, `accessory`, `sealed`
5. Set max CPC bids:

| Product Group | Max CPC | Action |
|---|---|---|
| `game` | — | Subdivide further (step 6) |
| `console` | **$0.35** | Set bid |
| `accessory` | **$0.25** | Set bid |
| `sealed` | **$0.30** | Set bid |
| `pokemon_card` | — | **EXCLUDE** (click the exclude/minus icon) |
| Everything else | — | **EXCLUDE** |

6. Click on the `game` product group → **Subdivide** → by **Custom label 0**
7. Set max CPC bids for game tiers:

| Product Group | Max CPC |
|---|---|
| `over_50` | **$0.55** |
| `20_to_50` | **$0.40** |
| `under_20` | **$0.20** |

8. Verify the final structure looks like:
```
All Products
├── game
│   ├── over_50    → $0.55
│   ├── 20_to_50   → $0.40
│   └── under_20   → $0.20
├── console         → $0.35
├── accessory       → $0.25
├── sealed          → $0.30
├── pokemon_card    → EXCLUDED
└── Everything else → EXCLUDED
```

---

## Task 5 — Import Negative Keywords (5 min, if not done by script)

If Task 3 Option A worked, the 334 negative keywords are already loaded. **Skip this task.**

If you built the campaign manually (Option B), load the negatives:

**Via Google Ads Editor (recommended):**
1. Download and install Google Ads Editor if not already: https://ads.google.com/intl/en/home/tools/ads-editor/
2. Download the account
3. Navigate to: Keywords and targeting → Campaign negative keywords
4. Click Import → From file → select `data/negative-keywords-google-ads-import.csv`
5. Review → Post changes

**Via Google Ads UI (slower but works):**
1. Campaign → `8BL-Shopping-All` → Keywords → Negative keywords
2. Click the + button
3. Copy-paste ALL terms from `docs/ads-negative-keywords-master.md` (each code block)
4. Set match type to Phrase (default)
5. Exception: set `free` and `review` to Exact match (to avoid blocking "free shipping" and "review policy" queries)

---

## Task 6 — Verify Everything Before Enabling (5 min)

Run through this checklist:

- [ ] Campaign `8BL-Shopping-All` exists and is PAUSED
- [ ] Budget is $14/day
- [ ] Bidding is Manual CPC with Enhanced CPC ON
- [ ] Networks: Search only (Display and YouTube Partners unchecked)
- [ ] Location: United States
- [ ] Product groups: game/console/accessory/sealed with correct bids, pokemon_card EXCLUDED
- [ ] Negative keywords: 300+ loaded
- [ ] Conversion tracking: at least Add to Cart, Begin Checkout, Page View show "Active" or "Recording"
- [ ] Merchant Center: 12K+ products approved (verified this morning)
- [ ] Circuit breaker: armed (check dashboard if accessible)

**If all green → tell Tristan the campaign is ready to enable.**
**Do NOT enable it yourself** — Tristan flips the switch.

---

## Hard guardrails

- **Do NOT enable the campaign** — create it as PAUSED, Tristan decides when to go live
- **Do NOT edit any files in `dashboard/`, `scripts/`, or `config/`** except `.env.local` for the OAuth token refresh
- **Do NOT run any Python scripts** except `create-shopping-campaign.py`
- **Do NOT change pricing, sales, or inventory**
- **Follow `docs/google-ads-campaign-setup-guide.md` exactly** for campaign settings

---

## When you're done

1. Write a summary to `docs/cowork-session-2026-04-16-pm.md` with:
   - Each task: GREEN / BLOCKED / SKIPPED
   - Campaign ID if created
   - Whether negative keywords loaded
   - Conversion tracking status
   - Whether the campaign is ready to enable

2. Commit and push:
```bash
git add docs/
git commit -m "Cowork 2026-04-16 PM: Shopping campaign created, conversion tracking re-fired"
git push
```

3. Tell Tristan: "Campaign is ready. Enable it in Google Ads when you're ready to go live."

---

## Success criteria

- [ ] Google Ads OAuth token refreshed and working
- [ ] Conversion tracking events re-fired (6 of 7)
- [ ] Campaign `8BL-Shopping-All` created as PAUSED
- [ ] Product groups subdivided with correct bid tiers
- [ ] 334 negative keywords loaded
- [ ] Pokemon singles excluded
- [ ] Handoff doc written
