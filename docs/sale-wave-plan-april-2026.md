# Sale Wave Plan — April/May 2026

**Drafted:** 2026-04-10
**Status:** Ready for review. DO NOT run `manage-sales.py --apply` without Tristan's explicit approval on which SKUs and depths.

---

## Strategic Framing

The store has ~5 orders in the past 6 months. The bottleneck is **traffic + trust**, not conversion rate on existing traffic. The sale wave must:

1. **Give cold visitors a reason to buy now** — first-time buyer psychology
2. **Look credible** — not a "gimmicky sale every day" storefront
3. **Coordinate with Google Ads launch** — sales drive the CTR bump that Google's algorithm interprets as relevance
4. **Not cannibalize margin on the stuff already selling** — the niche collector titles don't need discounts

**What this sale is NOT:** a blanket sitewide markdown. Retro game buyers compare prices item-by-item. A 10% off everything banner is noise, not a trigger.

**What this sale IS:** targeted, time-bound, differentiated by intent layer.

---

## The Four-Layer Sale Structure

### Layer 1 — "Entry Point" Sale (acquisition focus)

**Goal:** convert first-time visitors into first-time buyers.

- **Target:** items priced under $20 across all consoles
- **Depth:** 15% off
- **Exclusions:** Pokemon singles (already thin margin), sealed products (already tight)
- **Duration:** ongoing until Google Ads Month 1 is complete
- **Messaging:** "Starter Collection — 15% off everything under $20"
- **Script invocation (dry-run):**
  ```bash
  python3 scripts/manage-sales.py --max-price 20 --discount 15 --dry-run
  ```

**Why this works:** Under-$20 items are impulse buys. A first-time buyer who spends $17 on a Game Boy game becomes a customer record, a reviewable order, and an email address in the marketing flow. That's worth more than the $2.55 discount.

---

### Layer 2 — "Deals of the Week" (recurring rotation)

**Goal:** give the homepage a fresh hook every Monday; drive repeat visits.

- **Target:** 10 iconic/popular titles, rotated weekly
- **Depth:** 20% off
- **Selection:** pick from sort-collections.py top-ranked titles (Mario, Zelda, Sonic, Final Fantasy, Castlevania, Metroid, Mega Man, Street Fighter, Pokemon)
- **Duration:** 7 days per rotation
- **Script invocation:**
  ```bash
  python3 scripts/manage-sales.py --deals-of-week 10 --discount 20 --dry-run
  ```

**Why this works:** Repeat visits are how cold traffic warms up. "Deals of the Week" gives recurring visitors a reason to come back and gives email marketing a weekly hook ("This week's deals").

**Rotation cadence:** Every Monday morning, clear the previous week and run the script again to pick a new random set.

---

### Layer 3 — "Console Spotlight" (content marketing hook)

**Goal:** pair with podcast/social content. If the podcast covers N64 this week, discount N64.

- **Target:** one console at a time, top 20 popular titles
- **Depth:** 12% off
- **Duration:** 2 weeks (matches the podcast episode cycle)
- **Script invocation:**
  ```bash
  python3 scripts/manage-sales.py --console n64 --top 20 --discount 12 --dry-run
  ```

**Rotation idea (biweekly, matches podcast cycle):**
1. Weeks 1-2: N64 (first podcast episode was April 9, 2026)
2. Weeks 3-4: PS1
3. Weeks 5-6: SNES
4. Weeks 7-8: Sega Genesis
5. Weeks 9-10: Game Boy / GBA
6. Weeks 11-12: GameCube
7. Repeat or branch out

**Why this works:** Content → commerce is the cleanest conversion path for a small store. "We talked about [game] on the podcast, now it's 12% off" is a reason to click through.

---

### Layer 4 — "Hands Off" list (never discount these)

**Do not discount:**
- Niche collector titles that are already selling organically (Mystical Ninja, Phantasy Star Online, Galerians, Space Station Silicon Valley, Aidyn Chronicles)
- Anything over $75 market price (margin is already narrow after eBay fees on high-ticket items)
- Pokemon singles priced using 1.15x multiplier (already razor-thin)
- Sealed Pokemon products (supply is constrained, pricing follows market)
- Recently added products (<30 days, need time to find their natural price)

**Script protection:** `manage-sales.py` supports `--max-price` and `--search` filters; use those to exclude. Manually spot-check the dry-run output before applying.

---

## Launch Sequence

### Week of April 13, 2026 (if approved)

**Monday, April 13:**
1. Run `manage-sales.py --list-active` — see what's already on sale
2. Run `manage-sales.py --clear-all --dry-run` first, then `--apply` if output looks clean
3. Apply Layer 1 (under-$20, 15% off) — confirmed dry-run first
4. Apply Layer 2 (Deals of the Week rotation 1) — confirmed dry-run first
5. Update homepage hero to reflect new sale messaging (Shopify theme editor — manual or cowork)
6. Replace GameCube banner with a fresh "Starter Collection Sale" banner (manual — Affinity, see banner concepts doc)

**Tuesday, April 14:**
1. Verify sale is live on the storefront — spot check 5 products
2. Post sale announcement on Facebook + Instagram + TikTok (use `social-generator.py`)
3. Send email blast to subscriber list (if email list is verified — see cowork brief)

**Wednesday, April 15:**
1. Monitor traffic + conversions
2. Adjust if anything is broken

### Following Monday, April 20:
1. Clear Deals of the Week, rotate to new selection
2. Layer 1 stays active through Google Ads Month 1

### April 27:
1. Coordinate with podcast episode 2 drop — apply Layer 3 (N64 spotlight matches episode 1 topic list)
2. Rotate Deals of the Week again

---

## Sale Collection Management

The store needs a "Sale" collection for Google Shopping feed and for the site navigation. Verify:

- [ ] "Sale" collection exists on Shopify
- [ ] It's configured as a smart collection: "Products with compare_at_price > 0"
- [ ] It's added to the main nav
- [ ] It's included in the Merchant Center feed (so Google Shopping can surface discount prices)

`manage-sales.py` already sets compare_at_price, so the smart collection will populate automatically once sales are applied.

---

## Safety & Rollback

**Before every `--apply`:**
1. Run with `--dry-run` first
2. Review the product list in the output — spot-check for anything weird
3. If count > 200 products in a single action, PAUSE and ask for explicit go/no-go

**Rollback (if a sale goes wrong):**
```bash
python3 scripts/manage-sales.py --clear-all --dry-run
python3 scripts/manage-sales.py --clear-all --apply
```

This removes ALL compare_at prices across the store. Nuclear option but always available.

---

## Metrics to Watch (Week 1 of sale)

| Metric | Baseline | Target | Red flag |
|--------|----------|--------|----------|
| Orders/week | <1 | 3-5 | still <1 after 2 weeks |
| AOV | $101 | $80-$120 | drops below $60 (means sale is too deep) |
| Sale collection pageviews | unknown | measurable | zero visits to /collections/sale |
| Email signups from popup | unknown | 10+/week | zero (see cowork popup verification task) |

---

## Handoff: What Tristan approves

- [ ] Layer 1 target: under $20, 15% off — approve / adjust depth
- [ ] Layer 2 rotation: 10 iconic titles, 20% off — approve / adjust count
- [ ] Layer 3 console spotlight sequence — approve / reorder
- [ ] Layer 4 hands-off list — approve / add exclusions
- [ ] Launch date — April 13 tentative, confirm or shift

Once approved, this can all be executed via the existing scripts. Expected total execution time for Week 1: 30 minutes of script runs + spot-checking.
