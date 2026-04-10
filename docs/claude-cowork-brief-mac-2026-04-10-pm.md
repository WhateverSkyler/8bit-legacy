# Claude Cowork Brief — 2026-04-10 (afternoon session)

**For:** A second Claude Code session running on Tristan's machine with browser/UI access (Shopify admin, theme editor, Klaviyo/Mailchimp, Merchant Center, Google Ads UI, web)
**From:** Mac Claude (terminal session) — currently doing Python script work in `~/Projects/8bit-legacy`
**Context:** Tristan is splitting work across two Claude sessions today. This session is the **browser/UI worker**. The terminal worker is handling all Python scripts, GraphQL bulk updates, profit reports, scheduler ops, and memory updates — do not duplicate that work.

---

## Session start (mandatory)

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

Then read these in order:
1. `CLAUDE.md` — full project instructions
2. `docs/google-ads-launch-plan.md` — context for why the website work matters
3. `docs/sale-wave-plan-april-2026.md` — sale strategy your homepage work supports
4. `docs/sale-banner-concepts.md` — Concept 1 ("Starter Pack") is recommended
5. `docs/ecommerce-infrastructure-audit-2026-04-06.md` — prior audit; Task 5 needs an update
6. This brief

Per `CLAUDE.md`, 8bit-legacy syncs via GitHub. Pull at start, push at end.

---

## Hard guardrails (read before doing anything)

- **Do NOT touch any Python script in `scripts/`.** The terminal session owns those.
- **Do NOT run `manage-sales.py`, `optimize-product-feed.py`, `pokemon-card-importer.py`, or anything with `--apply`.** The terminal session is handling those, and parallel runs could double-update Shopify.
- **Do NOT touch Google Ads.** Conversion tracking + first launch is on Tristan's manual to-do. You can audit and document, not configure.
- **Never commit secrets.** `.env` files are gitignored — be careful if tokens appear in screenshots/logs.
- **Live theme changes:** always duplicate the current theme (Online Store → Themes → ⋯ → Duplicate) before editing. Get explicit Tristan approval before making any visible-to-customer change.
- **Brand:** orange `#ff9526`, sky-blue `#0EA5E9`, Nunito font, light theme only, Nintendo Switch-clean (not retro-kitsch).
- **Pull at start, push at end.**

---

## What the terminal session is currently doing (do NOT duplicate)

- **Running** `optimize-product-feed.py` against all 7,290+ Shopify products — adds `price_tier:`, `console:`, `category:`, `margin:` tags + SEO titles. ~60-90 min run. This is Phase 0 prep for Google Ads. Output: `data/logs/feed-optimize-apply-*.log`.
- Ran fresh profit report (Jan 1 → Apr 10): **2 orders, $139.58 revenue, $31.54 profit, 22.6% margin, $69.79 AOV** — mostly PS1 collector titles (Galerians + Metal Gear Solid), one Wii remote.
- Surfaced a `compare_at_price` bug: ~10 variants have `compare_at < price`, showing "negative discount" (e.g., Conker's CIB $438.99 with compare_at $219.99). Likely fallout from the CIB fix + price refresh sequence. Terminal session may write a cleanup script — leave it alone.
- Investigating VPS dashboard auth — `https://8bit.tristanaddi.com` returns nginx 401 (no basic-auth creds in `.env`).
- Will update memory files at session end.

---

## Your tasks (in priority order)

### Task A — Verify the 10% off email popup destination (PRIORITY: HIGH, ~25 min)

**Why this matters:** Tristan has never verified where collected emails go. Possible revenue leak — every visitor who entered an email and never received a code is a lost potential customer. With only 5 orders in 6 months, the email list may be the highest-leverage owned channel.

**Steps:**
1. Open the Shopify admin for `8bitlegacy.com` (Tristan should already be logged in via browser). If not, ask him to sign in manually.
2. **Online Store → Themes → Customize** — locate the popup block. Identify which app powers it (Shopify Forms / Klaviyo / Mailchimp / Privy / SmartrMail / Sumo / etc.).
3. Open whichever app is powering it and verify:
   - [ ] App is connected (OAuth still valid)
   - [ ] Subscriber count for the popup (last 30 days + total)
   - [ ] Subscribers landing in a usable list/segment
   - [ ] Welcome flow exists and is sending the 10% code
   - [ ] Welcome flow has actually fired (check send stats / queue)
   - [ ] The 10% discount code itself is valid and unexpired in Shopify → Discounts
4. Optional but valuable: check the discount code's "Used" count.

**Deliverable:** `docs/email-popup-audit-2026-04-10.md` with:
- App powering popup
- Subscriber count + welcome flow status
- Discount code validity + use count
- Concrete action items (e.g., "rebuild welcome flow", "switch to Klaviyo", "code expired — replace")

**Do NOT:**
- Modify any email app settings
- Send test emails to the real list
- Delete subscriber data
- Reset the discount code

---

### Task B — Verify "Sale" smart collection exists & is wired up (PRIORITY: HIGH, ~10 min)

The sale-wave plan depends on this. Without the smart collection, the upcoming sale layers won't surface in a single navigable spot.

**Steps:**
1. Shopify admin → Products → Collections
2. Look for a collection named "Sale" (or similar)
3. If it exists, verify:
   - [ ] It's a **smart** collection with the rule: `compare_at_price > 0` (or "Product on sale is true")
   - [ ] It's added to the main navigation menu
   - [ ] It's included in the Merchant Center / Google Shopping feed
4. If it does NOT exist, document that and propose creating it (don't create it without Tristan's go-ahead — collection creation triggers feed reprocessing).

**Deliverable:** Append findings to a new section in `docs/ecommerce-infrastructure-audit-2026-04-06.md` titled "Sale Collection Status — 2026-04-10" OR create `docs/sale-collection-status-2026-04-10.md`.

---

### Task C — Recheck the Shop sales channel (PRIORITY: MEDIUM, ~5 min)

**Context:** `docs/ecommerce-infrastructure-audit-2026-04-06.md` Task 5 had the Shop channel showing "Action needed" because of CIB variants being out of stock. CIB was fixed (`CLAUDE.md` completed list: "All CIB variants purchasable (6,112 fixed)"). Confirm the badge is gone.

**Steps:**
1. Shopify admin → Settings → Apps and sales channels → Shop
2. Check for "Action needed" / "Issue" badges
3. If gone: mark Task 5 complete in the audit doc
4. If still there: document the new reason

**Deliverable:** Update `docs/ecommerce-infrastructure-audit-2026-04-06.md` Task 5 in-place.

---

### Task D — Homepage redesign below "Deals of the Week" (PRIORITY: MEDIUM, ~50 min)

**Why:** Tristan said everything below "Deals of the Week" looks "half-assed." Visual polish needed before we drive cold traffic via Google Ads.

**Steps:**
1. Open `https://8bitlegacy.com` and scroll the full homepage. Take screenshots of every section below "Deals of the Week".
2. Open the theme customizer in Shopify and identify each section there.
3. List 3-5 specific issues making it feel half-finished. Likely candidates: inconsistent spacing, mismatched fonts, weak/placeholder imagery, broken layouts, duplicate or stub content, mismatched paddings, dark sections that violate the light-theme rule.
4. Propose fixes — **do not apply yet**. Write them in `docs/homepage-redesign-notes.md`:
   - Section name + screenshot
   - Specific issue
   - Specific fix (e.g., "swap placeholder image for Pokemon collection hero, change heading font from Arial to Nunito Bold, add 40px bottom padding")
   - Impact (high/medium/low) and effort (small/medium/large)
5. Rank fixes by impact/effort and ask Tristan which to apply first.
6. **Only if Tristan explicitly approves in-session:** duplicate the live theme first, then apply the approved fixes. Always preview on mobile and desktop before publishing.

**Brand anchors that must be honored:**
- Orange `#ff9526`, sky-blue `#0EA5E9`
- Nunito font family
- Light theme only
- Nintendo Switch-inspired clean aesthetic

**Do NOT:**
- Make unapproved live changes
- Delete or reorder sections without explicit approval
- Change brand colors or fonts
- Touch sections **above** "Deals of the Week" (those are working fine)

---

### Task E — VPS dashboard auth check (PRIORITY: LOW, ~10 min)

`https://8bit.tristanaddi.com` returns `nginx 401 Authorization Required`. Either basic auth was set up at the nginx layer and Tristan didn't share creds, or the dashboard's own auth is intercepting. The terminal session can't reach scheduler status without credentials.

**Steps:**
1. Try opening `https://8bit.tristanaddi.com` in the browser
2. If a basic-auth prompt appears, ask Tristan for the username/password
3. Once in, verify:
   - [ ] Dashboard loads
   - [ ] `/scheduler` page shows the 5 jobs healthy (last run + next run)
   - [ ] No tripped circuit breakers
4. If creds are reusable from a `.env`, document the env var name (don't paste the credential into the doc).

**Deliverable:** `docs/vps-dashboard-status-2026-04-10.md` (or append to the cowork session summary).

---

### Task F — Conversion tracking pre-flight check (PRIORITY: LOW, ~10 min)

**This is audit only — do not install or change anything.** The terminal session can't see the Shopify checkout page contents.

**Steps:**
1. Place a test item in cart on `8bitlegacy.com` (don't actually purchase). Use the browser's DevTools → Network tab → filter for `googleadservices` / `googleads` / `gtag`.
2. Look for the Google Ads conversion pixel firing on `Add to Cart` and on the `/checkouts/` step
3. If nothing fires, that confirms `Phase 0.1` of `google-ads-launch-plan.md` is still blocking
4. If something fires, screenshot it and note which conversion ID it sends to

**Deliverable:** Short note in `docs/google-ads-launch-plan.md` under a new "Phase 0.1 audit — 2026-04-10" section.

**Do NOT** complete a real test purchase. Just inspect the network traffic on the cart/checkout pages.

---

## When you're done

1. Commit only the docs you created/modified:
   ```bash
   git add docs/
   git status   # double check — make sure no scripts or .env got staged
   git commit -m "Cowork session: email popup audit, homepage notes, VPS check"
   git push
   ```
2. Write a short summary in `docs/cowork-session-summary-2026-04-10-pm.md`:
   - What you did
   - What you found
   - What's blocked and needs Tristan
3. If Tristan is still in the session, tell him what to review.

---

## Questions worth asking Tristan up front

- Which email tool is the popup supposed to be using? (helps you find it faster)
- Do you want me to apply homepage fixes I identify, or just document them?
- What're the VPS dashboard creds (or where in your password manager)?
- Any sections of the homepage to skip or prioritize?

---

## Reference: today's ground truth

- **Past 6 months:** 5 orders, ~$508 revenue, 22.7% margin, $101 AOV
- **Past 100 days (Jan 1 → Apr 10):** 2 orders, $139.58 revenue, $31.54 profit, $69.79 AOV
- **Best sellers:** Galerians (PS1), Metal Gear Solid (PS1), Wii remote
- **Diagnosis:** Store is cold. Bottleneck is traffic + trust, not conversion.
- **Live products:** 7,290 in Shopify (per latest fetch), ~6,121 retro games + ~1,176 Pokemon cards
- **Dashboard URL (auth required):** https://8bit.tristanaddi.com

Good luck. Ping me (terminal Claude) via Tristan if you hit anything blocking.
