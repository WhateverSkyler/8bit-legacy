# Google Ads Pre-Launch Checklist

**Drafted:** 2026-04-10 evening
**Purpose:** A single linear checklist — every item must be ✅ before clicking "Enable" on any campaign.
**Companion to:** `docs/google-ads-launch-plan-v2.md`

Work top-to-bottom. Do not skip items. If any item is blocked, stop and fix before proceeding.

---

## Section A — Account + tracking (20 min)

**State as of 2026-04-11 screenshot:** Account `822-210-2291` linked via `tristanaddi1` (owner listing). All 7 conversion actions EXIST but all 4 primary goal categories show **Misconfigured**, and Purchase / Begin Checkout / Add Payment Info are marked **Inactive** (tag has not fired a real event recently).

- [x] **A1.** Log into Google Ads account, access customer ID `822-210-2291` — done via `tristanaddi1` owner listing.
- [x] **A2–A3.** Google & YouTube Shopify app is connected to `822-210-2291` — done.
- [x] **A4.** All 7 conversion actions listed (Purchase, Begin Checkout, View Item, Add to Cart, Add Payment Info, Search, Page View) — done.
- [ ] **A5. 🚨 FIX THE "MISCONFIGURED" STATUS.** Each goal category needs at least one Primary action:
  - Google Ads → Goals → Conversions → Summary
  - For each row showing **Misconfigured** (Add to cart, Begin checkout, Page view):
    - Click row → **Edit goal**
    - Toggle the `Google Shopping App ...` secondary action to **Primary**
    - Save
  - For the Page view goal, at least `Google Shopping App Page View` should be Primary.
  - (Optional but recommended) Categorize the "Other" → Add Payment Info action under the Purchase funnel to clear the "categorize your Other conversion actions" warning.
- [ ] **A6. 🚨 FIRE LIVE EVENTS** to clear "Inactive" / "No recent conversions" badges:
  - Open https://8bitlegacy.com in an incognito window (no ad blockers)
  - Navigate a product page (→ Page View + View Item)
  - Use the store search bar (→ Search)
  - Click Add to Cart (→ Add to Cart)
  - Proceed to checkout with real email + address (→ Begin Checkout)
  - Enter a card, then abandon (→ Add Payment Info)
  - Wait **2–4 hours**
  - Return to Conversions page — events should show "No recent conversions" or "Recording", NOT "Inactive"
- [ ] **A7.** Merchant Center 5296797260 is still linked to Ads account `822-210-2291`. (Verify under Tools → Linked accounts → Merchant Center.)
- [ ] **A8.** "Customer lifecycle optimization needs 1,000+ audience members" warning can be **ignored for launch** — that's a Smart Bidding enhancement, not a blocker. Revisit in Phase 4 when email list grows.

**Do not proceed until A5 and A6 are ✅.** The promo credit is worthless without conversion tracking.

---

## Section B — Merchant Center feed health (15 min)

- [ ] **B1.** Log into Merchant Center 5296797260.
- [ ] **B2.** Products → Overview. Confirm ~7,689 active products, < 200 pending, < 50 disapproved.
- [ ] **B3.** Products → Diagnostics. Screenshot any item-level issues. Fix the top 5 by impact if they are material (missing images, incorrect availability, GTIN errors).
- [ ] **B4.** Products → Feeds. Confirm the Shopify feed has pulled in the last 24 hours.
- [ ] **B5.** Spot-check 10 random products in the Merchant Center product view. For each, confirm:
  - Title ends with "| 8-Bit Legacy" (SEO title from the feed optimizer)
  - Custom labels 0–3 are populated (`price_tier:X`, `console:X`, `category:X`, `margin:X`)
  - Image is present and not broken
  - Price matches Shopify
  - Availability is `in_stock`

---

## Section C — Homepage trust fixes (30 min)

**Status 2026-04-11 afternoon:** User reports homepage is now "good enough" — all C items below are accepted as done by user verdict. Re-audit if Mac Claude flags something specific in the site-wide review (see `docs/claude-cowork-brief-2026-04-11.md`).

- [x] **C1–C12.** Homepage updates accepted by user. Stale countdown, GameCube section, empty banners, visual polish — all resolved to user's satisfaction.

---

## Section D — Trust signal parity (Tristan decisions) (15 min)

- [ ] **D1.** **Decision: free shipping threshold.** Currently $50. Recommendation: lower to $35 or $40 to close the gap with DKOldies ($20). If keeping at $50, note the tradeoff (conversion rate disadvantage on $30–$49 products, which is most of the Winners list).
- [ ] **D2.** If changing: Shopify → Settings → Shipping and delivery → Free shipping threshold → update.
- [ ] **D3.** **Decision: return policy.** Currently 30 days. Recommendation: extend to 90 days to match Lukie Games.
- [ ] **D4.** If changing: Shopify → Settings → Policies → Refund policy → update text. Also update the announcement bar text and product page footer if hardcoded.
- [ ] **D5.** **Install a review app.** Recommendation: Shopify Product Reviews (free, native). Install → enable on product pages.
- [ ] **D6.** Seed first reviews: manually email the 5 past buyers asking if they'd leave a review. One sentence, casual. Even 2–3 reviews > 0.

---

## Section E — Safety system verification (10 min)

- [ ] **E1.** `dashboard/src/lib/safety.ts` has `max_daily_ad_spend` = $25 or lower.
- [ ] **E2.** Google Ads circuit breaker is armed (check dashboard settings page).
- [ ] **E3.** Test-trip the circuit breaker manually: simulate >$25 spend in the dashboard, confirm it flips to "TRIPPED" state and would pause campaigns via the API.
- [ ] **E4.** Reset the circuit breaker to "ARMED".
- [ ] **E5.** Confirm the `google-ads-sync` scheduled job (1 AM ET daily) is running without errors — check the VPS dashboard scheduler status page (if accessible), or Linux systemd logs.
- [ ] **E6.** Set up a Shopify webhook (or dashboard poll) to detect store downtime and trip the breaker if triggered.

---

## Section F — Campaign construction (45 min)

Work inside Google Ads UI. Create the two Phase 1 campaigns from scratch — do NOT import from templates, do NOT use the "Smart Campaign" or "Express" modes.

### F1 — Winners campaign

- [ ] **F1.1.** Campaigns → New campaign → Goal: Sales → Type: **Shopping** → Standard Shopping.
- [ ] **F1.2.** Name: `8BL-Shopping-Winners`
- [ ] **F1.3.** Merchant Center: 5296797260
- [ ] **F1.4.** Country of sale: United States
- [ ] **F1.5.** Networks: Search only (uncheck Display / YouTube / Partners)
- [ ] **F1.6.** Location targeting: United States (not all countries)
- [ ] **F1.7.** Bidding: **Manual CPC** (NOT Maximize conversions, NOT tROAS). Enable "Enhanced CPC" checkbox.
- [ ] **F1.8.** Daily budget: **$3.00**
- [ ] **F1.9.** Campaign priority: **High**
- [ ] **F1.10.** Ad group name: `winners-all`
- [ ] **F1.11.** Max CPC bid: **$0.75**
- [ ] **F1.12.** Product groups: subdivide by Item ID. Include ONLY the SKUs from `docs/ads-winners-curation-list.md`. Exclude "Everything else in All products".
- [ ] **F1.13.** Campaign → Keywords → Negative keywords → Add. Paste ALL 10 categories from `docs/ads-negative-keywords-master.md`. Use phrase match by default.
- [ ] **F1.14.** Campaign status: **Paused** (do not enable yet).

### F2 — Discovery campaign

- [ ] **F2.1.** Campaigns → New campaign → Goal: Sales → Shopping → Standard Shopping.
- [ ] **F2.2.** Name: `8BL-Shopping-Discovery`
- [ ] **F2.3.** Same MC, country, networks, location as F1.
- [ ] **F2.4.** Bidding: Manual CPC + Enhanced CPC
- [ ] **F2.5.** Daily budget: **$1.00**
- [ ] **F2.6.** Campaign priority: **Low**
- [ ] **F2.7.** Ad group name: `discovery-all`
- [ ] **F2.8.** Max CPC bid: **$0.35**
- [ ] **F2.9.** Product groups: subdivide by Custom label 2 (category). Exclude `category:pokemon_card`. Subdivide by Custom label 0 (price tier). Exclude `price_tier:under_20`. Effectively: include everything NOT Pokemon and NOT under $20. Also exclude the Winners SKUs individually (to avoid overlap with the High priority campaign).
- [ ] **F2.10.** Paste the same negative keyword list.
- [ ] **F2.11.** Campaign status: **Paused**.

---

## Section G — Content schedule alignment (user gate)

- [ ] **G1.** Social media calendar confirmed — at least 14 days of scheduled posts on Instagram, Facebook, TikTok, each linking back to the store.
- [ ] **G2.** Podcast Episode 2 record date confirmed (per user: postponed to next week from original April 23) and clips scheduled for YouTube Shorts + social.
- [ ] **G3.** At least one new product photography batch completed (per user: planned for tomorrow 2026-04-11) so social posts have fresh visuals.

**Do not proceed to Section H until G1–G3 are ✅.** This is the user's explicit launch gate.

---

## Section H — Launch (5 min)

- [ ] **H1.** Final dry-run the `ads-feed-audit.py` script if built — otherwise manually spot-check 5 Winners products in the live Merchant Center feed.
- [ ] **H2.** Confirm total daily spend commitment. **Promo mode (active until 2026-05-31):** $6 Winners + $4 Discovery = **$10/day during Weeks 1–2, ~$140** — escalating to $14/day Weeks 3–7 as Remarketing + PMax-Test come online. **Post-promo baseline:** $3 Winners + $1 Discovery = $4/day. See `docs/google-ads-launch-plan-v2.md` → "Promo-credit budget overlay".
- [ ] **H3.** Set `8BL-Shopping-Winners` daily budget to **$6** (promo mode).
- [ ] **H4.** Set `8BL-Shopping-Discovery` daily budget to **$4** (promo mode).
- [ ] **H5.** Enable `8BL-Shopping-Winners` campaign.
- [ ] **H6.** Enable `8BL-Shopping-Discovery` campaign.
- [ ] **H7.** Screenshot the campaigns dashboard (timestamp + status) for the record.
- [ ] **H8.** Note the launch date in `docs/` as a new handoff entry for the next session.
- [ ] **H9.** Set a reminder for +24 hours to do the first daily review.
- [ ] **H10.** Add 2026-05-31 to the calendar as the promo-credit expiry — drop budgets back to baseline on 2026-06-01.

---

## Abort conditions

Stop and do NOT launch if any of these appear:

- 🚨 Any A1–A7 item is red (account linking or conversion tracking broken)
- 🚨 More than 100 products are in "disapproved" state in Merchant Center (B2)
- 🚨 The homepage still shows the `2025/05/07` countdown timer (C3)
- 🚨 The dashboard circuit breaker is not armed or is in error state (E2)
- 🚨 Social + podcast content is not scheduled (G1–G2)
- 🚨 Shopify store has any active downtime or partial outage

---

## After launch: first 24 hours

- Check spend every 6 hours. It should match the $4/day pace, not $0 (feed issue) and not $8 (budget overspend anomaly).
- Check Google Ads → Campaigns → Search terms (Winners campaign) at 24 hours. Expect 5–15 search terms. Review each; if anything looks irrelevant, add to negatives immediately.
- Check Merchant Center feed approval state at 24 hours — sometimes launching a campaign surfaces disapproval warnings that were silent before.
- If spend is $0 after 24 hours: the feed or the bid is too low. Check Auction Insights for Winners campaign; if impression share is 0%, raise max CPC to $1.00 temporarily.
- If spend is $8+ (2x budget) with 0 conversions: pause Winners and investigate before the 48h circuit breaker trips.

---

## Quick reference — launch day contact list

- **Shopify admin:** https://admin.shopify.com/store/dpxzef-st
- **Google Ads:** https://ads.google.com (login: `sideshowtristan@gmail.com`)
- **Merchant Center:** https://merchants.google.com (account 5296797260)
- **8-Bit Legacy storefront:** https://8bitlegacy.com
- **Dashboard:** https://8bit.tristanaddi.com (requires auth — currently blocked, see VPS dashboard status doc)
- **Circuit breaker settings:** `dashboard/src/lib/safety.ts`
- **This checklist:** `docs/ads-pre-launch-checklist.md`
- **Launch plan:** `docs/google-ads-launch-plan-v2.md`
- **Winners list:** `docs/ads-winners-curation-list.md`
- **Negative keywords:** `docs/ads-negative-keywords-master.md`

---

## Estimated time to green

Assuming no surprises:
- Section A: 10 min (but requires Google Ads account admin access — bottleneck if 2FA lost)
- Section B: 15 min
- Section C: 30 min (theme editor)
- Section D: 15 min (decisions + Shopify settings)
- Section E: 10 min (verification)
- Section F: 45 min (Google Ads UI campaign construction)
- Section G: gated on user's content schedule
- Section H: 5 min

**Total hands-on work:** ~2 hours. Gate on G (content schedule) is likely the longest-duration wait.
