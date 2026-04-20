# Claude Cowork Brief — 2026-04-20 (Google Ads Launch Finalization)

**For:** Claude Code running on Tristan's Mac with browser/UI automation capability
**From:** Claude Opus running in the repo's main session
**Written:** 2026-04-20 ~3:15 PM EDT
**Goal:** Clear the last 5 pre-launch blockers on the Google Ads campaign so Tristan can flip `8BL-Shopping-Games` from Paused to Enabled with full confidence in the architecture. Research is complete (`docs/ads-launch-research-2026-04-20.md`) — this brief executes the browser/UI work that the main session can't do.

---

## Session start — mandatory

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

If pull fails, STOP and tell Tristan.

**Read these files, in order:**
1. `CLAUDE.md` — project rules
2. `docs/ads-launch-research-2026-04-20.md` — THE context for this session. Everything below assumes you've read it.
3. `docs/claude-cowork-brief-2026-04-20-zernio-setup.md` — pattern reference for cowork workflow
4. `data/negative-keywords-google-ads-import-v2.csv` — 334 negatives, already renamed for `8BL-Shopping-Games`
5. `data/merchant-center-cib-exclusion.csv` — will exist once the main session's generator finishes (see Task 4)
6. This brief.

---

## Pre-flight confirmations with Tristan

1. **Campaign rename OK?** Current name is `8BL-Shopping-All` (Campaign ID `23766662629`, Paused). Plan is to rename → `8BL-Shopping-Games`. If Tristan prefers a different name, use that and update the negatives CSV's campaign column to match.
2. **Budget $20/day — confirmed by Tristan 2026-04-20 3:21 PM.** Rationale: $700 ÷ 42 days = $16.67 theoretical, but Google under-spends base budget 15-30% during learning, so $20/day gives headroom to reliably burn the full credit before 2026-05-31 expiry. Do not re-ask.
3. **No test purchase needed** (confirmed with Tristan 2026-04-20). Instead, during Task 3 — when you click into `Google Shopping App Purchase` conversion action — just verify it shows status **`Created`** (pixel wired up, awaiting real-customer data). If it shows `Misconfigured` / `Inactive due to error` / `Needs attention`, THEN escalate. `Created` + awaiting data is fine — first real customer order will flip it to Recording naturally.

---

## Task 1 — Refresh the Google Ads OAuth token 🔴 (~5 min, CRITICAL)

The existing refresh token in `config/.env` and `dashboard/.env.local` returns `invalid_grant`. Blocks: API-based campaign edits, dashboard monitoring jobs, circuit breaker's automated pause. The main session can't do this — needs a live browser sign-in.

### Steps

1. Construct the auth URL (main session already generated one — if the `prompt`/Tristan already visited, skip; otherwise):
   ```
   https://accounts.google.com/o/oauth2/v2/auth?client_id=585154028800-30b12ji9qdncj1ng4lv8f8i3atnafce9.apps.googleusercontent.com&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fadwords&access_type=offline&prompt=consent
   ```
2. Sign in with `sideshowtristan@gmail.com` (the account that owns Google Ads `822-210-2291`)
3. Grant the AdWords scope
4. Google displays an auth code on the consent page — copy it
5. Exchange for refresh token via terminal on Mac:
   ```bash
   cd ~/Projects/8bit-legacy
   CID=$(grep "^GOOGLE_ADS_CLIENT_ID=" config/.env | cut -d= -f2)
   SECRET=$(grep "^GOOGLE_ADS_CLIENT_SECRET=" config/.env | cut -d= -f2)
   AUTH_CODE="<paste the code here>"

   curl -s -X POST "https://oauth2.googleapis.com/token" \
     -d "code=${AUTH_CODE}" \
     -d "client_id=${CID}" \
     -d "client_secret=${SECRET}" \
     -d "redirect_uri=urn:ietf:wg:oauth:2.0:oob" \
     -d "grant_type=authorization_code" | python3 -m json.tool
   ```
6. Copy the `refresh_token` value from the response
7. Update BOTH env files:
   ```bash
   NEW_TOKEN="<paste the new refresh_token>"
   sed -i.bak "s|^GOOGLE_ADS_REFRESH_TOKEN=.*|GOOGLE_ADS_REFRESH_TOKEN=${NEW_TOKEN}|" config/.env
   sed -i.bak "s|^GOOGLE_ADS_REFRESH_TOKEN=.*|GOOGLE_ADS_REFRESH_TOKEN=${NEW_TOKEN}|" dashboard/.env.local
   rm -f config/.env.bak dashboard/.env.local.bak
   ```
8. Also update the VPS dashboard's `.env.local` (if accessible):
   ```bash
   # Tristan can do this via SSH to the VPS, or we flag it for him
   ```
9. Verify:
   ```bash
   curl -s -X POST "https://oauth2.googleapis.com/token" \
     -d "client_id=${CID}&client_secret=${SECRET}&refresh_token=${NEW_TOKEN}&grant_type=refresh_token" \
     | python3 -c "import sys,json; d=json.load(sys.stdin); print('VALID' if 'access_token' in d else 'FAIL'); print(d)"
   ```
   Expect `VALID` + an access_token.

---

## Task 2 — Merchant Center diagnostics audit 🟡 (~10 min)

1. Log into Merchant Center at https://merchants.google.com/ (account 5296797260)
2. Navigate to **Products → Diagnostics**
3. Screenshot the page
4. Record:
   - Total active products
   - Products with item-level issues — count AND top 3 reasons (if any)
   - Account-level issues — specifically, anything about Shopping ads program status
5. If **> 50 disapproved** or **any account-level issue**: STOP and flag to Tristan. Do NOT enable the campaign.
6. If **< 50 disapproved** with normal item-level reasons (missing attributes on long-tail SKUs, etc.): note them for later cleanup, proceed.

**Also verify:** Growth → Manage programs → Shopping ads program status shows **Active** (not Pending/Suspended).

---

## Task 3 — Conversion tracking "Recording" verification 🔴 (~10 min + wait)

Events were re-fired 2026-04-16 but we never confirmed they actually moved from "Inactive"/"Misconfigured" to "Recording". Without this, campaign spend is effectively blind.

1. Log into Google Ads → account 822-210-2291
2. Navigate to **Goals → Conversions → Summary**
3. For each of the 4 primary goal categories (Purchase, Add to Cart, Begin Checkout, Page View):
   - Record the current state: `Recording` / `No recent conversions` / `Inactive` / `Misconfigured`
4. If any goal shows **`Inactive`**: re-fire events in incognito:
   - https://8bitlegacy.com in an incognito window (no ad blockers)
   - Navigate a product page (fires Page View + View Item)
   - Search bar (fires Search)
   - Add to Cart
   - Proceed to checkout, enter email + address (fires Begin Checkout)
   - Enter card, abandon (fires Add Payment Info)
   - Wait 2-4 hours, re-check
5. If any goal shows **`Misconfigured`**: click Edit Goal, toggle the `Google Shopping App <X>` action to Primary, save.
6. **Purchase goal**: will show Inactive until a real order happens. Tristan's option: place a $5-10 real order + refund afterward (fires Purchase end-to-end) — recommended before Day 0. Otherwise Purchase flips to Active on first real customer order.

**Do NOT proceed to Task 5 (enable campaign) unless all 4 goals are `Recording` or `No recent conversions`.**

---

## Task 4 — Upload CIB exclusion supplemental feed to Merchant Center 🟡 (~10 min)

Main session's `scripts/generate-cib-exclusion-feed.py` outputs `data/merchant-center-cib-exclusion.csv` — a list of CIB variant offer IDs that should be excluded from paid Shopping ads while remaining on Free Listings.

### Verify the file exists first:
```bash
ls -la data/merchant-center-cib-exclusion.csv
wc -l data/merchant-center-cib-exclusion.csv
head -3 data/merchant-center-cib-exclusion.csv
```

Expected: ~6,100 rows. If the file doesn't exist yet, flag to Tristan — the generator may still be running or have failed.

### Before uploading — sanity check ONE offer ID against Merchant Center

1. Merchant Center → Products → All products
2. Find any CIB variant in the product list (filter by "Complete" or "CIB" in title)
3. Click it → note the **ID / Offer ID** field
4. Compare to what the CSV claims: look up the same product in the CSV (by handle or product ID suffix)
5. If the formats don't match: STOP. The generator used pattern `shopify_US_{productNum}_{variantNum}`; if MC uses a different format (e.g., `shopify_US_{shopId}_{productNum}_{variantNum}`), we need to regenerate. Flag to Tristan and the main session.

### Upload

1. Merchant Center → **Products → Feeds**
2. Click **Add supplemental feed**
3. Name: `CIB Shopping Exclusion`
4. Input method: **Upload file**
5. Select `data/merchant-center-cib-exclusion.csv` from the Mac
6. Target feeds: select the primary Shopify feed
7. Save
8. Schedule: Daily refresh (set a reminder to upload updated CSVs periodically as new CIB products are added to the store)

### Post-upload verification (after ~24h)

- Return to Merchant Center → Products → All products
- Filter by `Disapproved for: Shopping ads` + search for a CIB variant
- Confirm the variant shows `Disapproved for Shopping ads` while still `Active for Free listings`

---

## Task 5 — Google Ads UI work 🔴 (~25 min)

### 5.1 Rename the campaign

1. Google Ads → Campaigns → `8BL-Shopping-All` → Edit → Name: `8BL-Shopping-Games`

### 5.2 Update budget

1. Campaigns → `8BL-Shopping-Games` → Settings → Daily budget
2. Change from `$14` → **`$20`**
3. Save

### 5.3 Product group subdivisions (the bid tree)

The campaign was mid-save on subdivisions when suspension hit. Redo from scratch:

1. Campaigns → `8BL-Shopping-Games` → Ad groups → `all-products` → Product groups tab
2. Click on **"All products"** → **Subdivide** → by **Custom label 2** (category)
3. Bulk add values: `game`, `console`, `accessory`, `sealed`, `pokemon_card` (one per line)
4. After save, set each:
   | Category | Action |
   |----------|--------|
   | `game` | Subdivide further (next step) |
   | `pokemon_card` | **EXCLUDE** |
   | `console` | **EXCLUDE** |
   | `accessory` | **EXCLUDE** |
   | `sealed` | **EXCLUDE** |
   | Everything else | **EXCLUDE** |
5. Click into `game` → Subdivide → by **Custom label 0** (price_tier)
6. Bulk add: `over_50`, `20_to_50`, `under_20`
7. After save, set each:
   | Price tier | Max CPC |
   |------------|---------|
   | `over_50` | **$0.35** |
   | `20_to_50` | **$0.12** |
   | `under_20` | **EXCLUDE** |
   | Everything else | **EXCLUDE** |
8. Save the whole tree

### 5.4 Import negative keywords

Use Google Ads Editor (desktop app) — fastest path for 334 keywords:

1. Download Google Ads Editor if not already installed: https://ads.google.com/intl/en/home/tools/ads-editor/
2. Download account → select `8BL-Shopping-Games`
3. Keywords and targeting → **Campaign negative keywords** → Import → **From file**
4. Select `data/negative-keywords-google-ads-import-v2.csv`
5. Review → Post changes

**Fallback (manual, slower):** Google Ads UI → Campaign → Keywords → Negative keywords → + → paste all terms from the CSV (skip the "Campaign" and "Match Type" columns; Google Ads UI accepts one term per line and the match type is inferred from Phrase if you paste quoted).

### 5.5 Verify campaign settings before Tristan sees it

Walk through Campaign Settings one more time and confirm:
- [ ] Name: `8BL-Shopping-Games`
- [ ] Type: Standard Shopping
- [ ] Networks: **Google Search Network only** (no Search Partners, no Display)
- [ ] Location: United States
- [ ] Bidding: **Manual CPC** (no Enhanced CPC — Google deprecated it for Shopping)
- [ ] Daily budget: $20
- [ ] Campaign priority: High
- [ ] Status: **Paused**

### 5.6 DO NOT ENABLE

Leave status as Paused. Tristan flips it Enabled only after:
- Tasks 1-4 are all green
- `ads-launch-research-2026-04-20.md` Part 5 checklist is complete
- Safety.ts is patched and the dashboard is redeployed to VPS (main session's followup)

---

## Task 6 — Spot-check 5 Winners landing pages 🟢 (~10 min)

Pick any 5 of the Winners from `docs/ads-winners-curation-list.md` and visit each product page on `https://8bitlegacy.com` in a FRESH incognito window. For each:

- [ ] Page loads fast (< 3 sec to interactive)
- [ ] Game Only variant is selected by default, showing the lower price
- [ ] Switching to Complete (CIB) variant shows the higher price correctly (variant-price display fix is working)
- [ ] Trust signals visible: "Free shipping over $35" / "90-day returns" / "1-year warranty"
- [ ] Product image(s) render
- [ ] Add to Cart button works (don't complete, just confirm it adds)
- [ ] No broken elements (missing CSS, 404 resources, broken links)

If ANY Winner has a broken landing page: flag to Tristan, do NOT enable campaign.

---

## Hard guardrails

- **Do NOT enable the campaign.** Leave Paused at the end of this session. Tristan flips it.
- **Do NOT commit any secrets** (API keys, refresh tokens, auth codes). All stay in `config/.env`, `dashboard/.env.local`, or local terminal sessions.
- **Do NOT raise the daily budget above $20** without Tristan's approval.
- **Do NOT change safety.ts** — main session has already patched it; changes get rebuilt + redeployed separately.
- **Do NOT import keywords with a campaign name other than `8BL-Shopping-Games`** — the CSV will pair them with the wrong campaign.
- **Do NOT skip Task 3** — launching without confirmed conversion tracking means blind spend.

---

## When you're done

1. Commit any repo docs you produced:
   ```bash
   git add docs/cowork-session-2026-04-20-ads-launch.md
   git status  # confirm no .env / secrets
   git commit -m "Cowork 2026-04-20: Google Ads launch setup complete (campaign Paused)"
   ```
   (Tristan will push at EOD per prior direction.)

2. Write a handoff note at `docs/cowork-session-2026-04-20-ads-launch.md` with:
   - Per-task GREEN / BLOCKED / SKIPPED + reason
   - Current state of each of the 4 conversion goals
   - Merchant Center product count + issue count
   - Whether the new OAuth refresh token was tested and is valid
   - Whether product group subdivisions saved cleanly
   - Whether negatives imported
   - Whether CIB supplemental feed uploaded
   - The 5 Winners landing pages checked + pass/fail
   - **Final recommendation: is the campaign ready to enable, or is something still blocking?**

3. Tell Tristan in chat:
   - Summary of task statuses
   - Single sentence on whether to enable or wait
   - Any outstanding questions or decisions

---

## Success criteria

- [ ] Google Ads OAuth refresh token refreshed, valid, written to both `.env` files
- [ ] Merchant Center diagnostics audited, < 50 disapproved, no account-level issues
- [ ] All 4 conversion goals: Recording or No recent conversions (NOT Inactive/Misconfigured)
- [ ] Campaign renamed to `8BL-Shopping-Games`, budget $20, settings verified
- [ ] Product group subdivisions saved: over_50 = $0.35, 20_to_50 = $0.12, everything else EXCLUDED
- [ ] 334 negative keywords imported
- [ ] CIB supplemental feed uploaded (or flagged if format doesn't match)
- [ ] 5 Winners landing pages spot-checked + passing
- [ ] Campaign status: Paused
- [ ] Handoff note written + pushed
- [ ] Clear go/no-go recommendation surfaced to Tristan
