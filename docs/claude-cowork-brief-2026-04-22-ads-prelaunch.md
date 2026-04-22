# Claude Cowork Brief — 2026-04-22 — Ads Pre-Launch Verification

## The task in one sentence
Clear the 5 pre-launch gates so Tristan can flip `8BL-Shopping-Games` from Paused to Enabled — all browser/admin UI work the main session can't do.

## Context (read first — critical)
Main session built the campaign end-to-end via API today. Config is verified via `python3 scripts/ads_preflight_check.py` (18/18 checks pass). The campaign is PAUSED and must remain PAUSED at the end of your session — Tristan flips it himself once your work confirms it's safe.

Full build state + rationale: **`docs/ads-launch-master-plan-2026-04-22.md`**. Read sections 1, 2, and 10 before starting.

## Hard guardrails
- **DO NOT enable the campaign.** Leave Paused. Tristan flips it.
- **DO NOT modify any campaign settings** — bids, budget, negatives, listing tree, etc. Main session set those to the plan; don't touch.
- **DO NOT touch any other Shopify/Ads config** beyond what's listed below.
- **DO NOT commit any secrets.**
- **DO NOT pause or re-enable any other campaign.** There's only one (`8BL-Shopping-Games`) — don't touch it.
- If something fails, STOP and report — don't improvise a workaround.

## Session start
```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
python3 scripts/ads_preflight_check.py  # sanity — should be 18/18 pass
```

If preflight shows any failures, STOP and flag to Tristan before doing anything else.

---

## Task 1 — Merchant Center diagnostics audit 🟡 (~5 min)

1. Log into **https://merchants.google.com/** as `tristanaddi1@gmail.com`
2. Select account `5296797260` (top-left switcher)
3. Navigate: **Products → Diagnostics**
4. Screenshot the page
5. Record in your handoff:
   - Total active products (expected: ~12K)
   - Item-level issue count + top 3 reasons (if any)
   - Any **account-level issues** (red, top banner)
6. Also check: **Growth → Manage programs → Shopping ads** status should be **Active** (not Pending / Paused / Suspended)

**Gate decision:**
- `>50 disapproved items` OR `any account-level issue` OR `Shopping ads NOT Active` → 🔴 DO NOT clear gate. Flag to Tristan.
- `<50 disapproved with normal item-level issues (missing attrs on long-tail)` AND `no account issues` AND `Shopping ads Active` → ✅ gate cleared. Note top 3 disapproval reasons for cleanup later.

---

## Task 2 — Upload CIB exclusion supplemental feed 🟡 (~5 min)

File already exists: **`data/merchant-center-cib-exclusion.csv`** (6,088 rows, `id,excluded_destination` format — marks each CIB variant with `excluded_destination=Shopping_ads`).

### Before uploading — 1-minute sanity check
1. Merchant Center → Products → All products
2. Filter by: search for any CIB variant title (e.g., `"Complete"` or `"CIB"` in title)
3. Click ONE CIB variant and note its **Offer ID** / **Item ID**
4. `cat data/merchant-center-cib-exclusion.csv | head -5` — compare format
5. If the format doesn't match (e.g., MC uses `shopify_US_{shopId}_{productNum}_{variantNum}` but CSV uses `shopify_US_{productNum}_{variantNum}` without shopId), STOP and flag to main session — regenerator needs to re-run. Expected format: `shopify_US_<productId>_<variantId>` per `scripts/generate-cib-exclusion-feed.py`.

### Upload
1. Merchant Center → **Products → Feeds**
2. Click **+ Add supplemental feed**
3. Name: `CIB Shopping Exclusion`
4. Country: **United States**, Language: **English**
5. Input method: **Upload file**
6. Select the CSV from `~/Projects/8bit-legacy/data/merchant-center-cib-exclusion.csv`
7. Target feeds: select the primary Shopify feed
8. Save

### Schedule daily refresh (if option offered)
Not critical, but if the UI offers a daily fetch schedule, set it. The CSV regenerates when main session re-runs `scripts/generate-cib-exclusion-feed.py`.

**Gate decision:**
- Format match + upload success → ✅ cleared. Note: full propagation takes 24-48h; that's fine, campaign can go live before propagation completes.
- Format mismatch → 🔴 flag to Tristan + main session.

---

## Task 3 — Fire test pixel events in incognito 🟡 (~5 min)

This is the **most important gate** — without it we launch blind on conversion attribution.

1. Open **https://8bitlegacy.com** in a **FRESH incognito window** (Cmd+Shift+N / Ctrl+Shift+N) — no ad blockers, no browser extensions
2. Walk through this exact path, slowly:
   1. Homepage loads (fires `page_view`)
   2. Click into ANY product (e.g., Mystical Ninja N64, Galerians PS1) — fires `view_item`
   3. Click the store's search bar, type a game name, search — fires `search`
   4. Click **Add to Cart** on a product — fires `add_to_cart`
   5. Click cart icon, then **Checkout**
   6. Fill in fake-but-valid-looking: email (use a throwaway), shipping name + address (any real US address — doesn't matter, no order will be placed)
   7. Click continue → fires `begin_checkout`
   8. On payment step, enter a dummy card (don't use your real card): use test digits like `4242 4242 4242 4242`, any future expiry, any 3 digits for CVC
   9. Click continue to fire `add_payment_info`. The payment will fail (that's fine — we just need the event to fire before submission).
   10. **ABANDON** — close the tab. Do NOT complete a real purchase.

**Purchase action is expected to stay Inactive until a real order happens.** That's fine — first real customer flips it.

### Immediately after firing events
Log the exact time in your handoff. Events propagate in 2-4 hours.

---

## Task 4 — Verify conversion tracking (wait 2-4h after Task 3, then check) 🔴

After the 2-4h wait window from Task 3:

1. Log into **https://ads.google.com**
2. Switch to account `822-210-2291` (8-Bit Legacy)
3. Navigate: **Tools & Settings (wrench icon) → Measurement → Conversions → Summary**
4. Record status for each of the 4 goal categories:

| Goal | Primary action | Expected status |
|---|---|---|
| Purchase | Google Shopping App Purchase | Inactive (OK — flips on first real order) |
| Add to cart | Google Shopping App Add To Cart | **Recording** or **No recent conversions** |
| Begin checkout | Google Shopping App Begin Checkout | **Recording** or **No recent conversions** |
| Page view | Google Shopping App Page View | **Recording** or **No recent conversions** |

Also verify: `Add Payment Info` under "Other" category shows Recording or No recent conversions.

**Gate decision:**
- All 4 non-Purchase goals show **Recording** or **No recent conversions** → ✅ gate cleared. Launch-ready.
- Any shows **Inactive** or **Misconfigured** or **Needs attention** → 🔴 gate BLOCKED. Fire events again per Task 3, wait another 2h, re-check. If still failing after 2 retries, flag to Tristan — the pixel is genuinely broken and we shouldn't launch.

---

## Task 5 — Verify 8BITNEW promo code is active 🟢 (~1 min)

Main session's API token lacks `read_discounts` scope, so we need you to verify in the Shopify admin UI directly.

1. Log into **https://admin.shopify.com** → 8-Bit Legacy store
2. Left nav: **Discounts**
3. Search for **`8BITNEW`**
4. Click it. Confirm:
   - Status: **Active**
   - Start date: past
   - End date: either none, or far in the future (>30 days out)
   - Value: 10% off
5. If **expired, disabled, or missing**: flag to Tristan. The post-launch plan mentions promoting this code as a Merchant Center promotion (CTR lift) — it's non-blocking for launch, but we want it fixed before the MC promotion work starts.

---

## Task 6 — Optional: submit `8BITNEW` as a Merchant Center Promotion 🟢 (if scoped)

Only do this if Tasks 1-5 are all green AND you have spare time AND the 8BITNEW code was confirmed Active in Task 5.

1. Merchant Center → **Marketing → Promotions**
2. Click **+ New promotion** (may also be "Create promotion" button)
3. Fill out:
   - **Promotion ID:** `8BITNEW-FIRST-ORDER`
   - **Promotion title:** `10% off your first order`
   - **Promotion effective dates:** today → 90 days from today
   - **Applicability:** All products
   - **Promotion code:** `8BITNEW`
   - **Redemption channel:** Online
   - **Minimum purchase amount:** none (or match whatever Shopify config says)
4. Submit for Google review
5. Note in handoff: review typically takes 1-3 days; ribbon appears on Shopping ads once approved.

If this flow isn't available or requires a form Tristan hasn't pre-filled (country/store info for Promotions), just note it and skip — Tristan can do it.

---

## When you're done

1. Run the preflight once more:
   ```bash
   python3 scripts/ads_preflight_check.py
   ```
   Should still be 18/18 pass (you haven't touched anything that'd affect those checks).

2. Write a handoff at `docs/cowork-session-2026-04-22-ads-prelaunch.md` with:
   - Per-task GREEN / BLOCKED / SKIPPED + reason
   - Merchant Center product counts + top disapproval reasons
   - CIB feed upload status + target feed name
   - Exact time events were fired + status of each conversion goal when re-checked
   - 8BITNEW promo code status
   - **Final recommendation: SAFE TO ENABLE, or BLOCKED ON X?**

3. Commit + push:
   ```bash
   git add docs/cowork-session-2026-04-22-ads-prelaunch.md
   git status   # verify no .env / secrets
   git commit -m "Cowork 2026-04-22: ads pre-launch gates cleared"
   git push
   ```

4. Tell Tristan in chat:
   - One-sentence summary of each task (Done / Blocked)
   - The go/no-go recommendation
   - Any screenshots worth saving

## Success criteria
- [ ] Merchant Center diagnostics audited; no account-level issues; disapprovals <50
- [ ] CIB supplemental feed uploaded OR format mismatch flagged
- [ ] Test events fired in incognito at a logged timestamp
- [ ] 4 conversion goals verified Recording/No-recent-conv (not Inactive) after wait
- [ ] 8BITNEW status confirmed in Shopify admin
- [ ] Handoff doc written + pushed
- [ ] Campaign still PAUSED
- [ ] Clear GO / NO-GO recommendation in chat to Tristan
