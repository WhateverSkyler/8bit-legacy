# ⚠️ DEPRECATED 2026-04-23 — do not use

> **This document describes a 2-campaign plan (Winners + Discovery) that was superseded on 2026-04-16.**
> The live campaign is a single Standard Shopping campaign (`8BL-Shopping-Games`) that targets
> ALL games tagged `category:game` via price-tier bidding ($0.35 for over_50, $0.08 for 20_to_50,
> under_20 excluded). There is no curated Winners SKU list in the live campaign.
>
> Source of truth: `docs/ads-launch-master-plan-2026-04-22.md`.
>
> Kept for historical reference only. Do not lean on "Winners list" context in new work.

---

# Google Ads — Phase 1 "Winners" Curation List (historical)

**Drafted:** 2026-04-10 evening
**Purpose:** Hand-picked product list for the Phase 1 `8BL-Shopping-Winners` Standard Shopping campaign. Prioritizes high-confidence conversion candidates, excludes anything with structural problems.

## Selection logic

A product qualifies for the Winners list if it meets **all** of these:

1. **Proven or plausible organic demand** — either already selling organically at full price (Galerians, Mystical Ninja, Phantasy Star Online, Aidyn Chronicles, Metal Gear Solid PS1), or a deep-cut cult classic in the same vein (high enthusiast affinity, low mainstream awareness, low competitor coverage).
2. **Price in the $30–$175 band** — under $30 leaves no margin for ad cost at our AOV math; over $175 is too much commitment for a cold store with zero reviews.
3. **Long-tail search term economics** — the product's name has to be specific enough that search volume is low and ad auction is uncompetitive. "Mystical Ninja N64" has ~$0.30 CPC. "Zelda Ocarina of Time N64" would be $2+. We're hunting the former.
4. **No Pokemon singles** — 1.15x margin is too thin to support any ad cost.
5. **Not in the Hands-Off list** from `sale-wave-plan-april-2026.md` — these are already self-sustaining organic sellers. Adding ad cost to a product that sells at full price without ads just burns money without incremental revenue.

Wait — that last point conflicts with the first. Let me resolve it.

**Resolution:** The organic winners ARE eligible for the Winners ads campaign specifically because we want to scale their existing demand signal, not because we're trying to spark new demand. But we should NOT discount them in the sale wave. So they're "ads YES, sales NO." Different levers.

## The List — verified 2026-04-11 against live Shopify

**Audit data:** `docs/ads-winners-audit-2026-04-11.md` / `data/ads-winners-audit-2026-04-11.json`

**Status legend:**
- ✅ LIVE — product is active, in stock, imaged, correctly tagged → ready for ads
- ⚠️ TAG FIX — product exists but has a tag bug that needs correcting before ads launch
- ❌ MISSING — product is not in the store catalog; either import or remove from Winners list

| # | Title | Console | Price | Handle | Status |
|---|---|---|---|---|---|
| 1 | Galerians (Game Only) | PS1 | $59.99 | `galerians-ps1-game` | ✅ LIVE |
| 2 | Galerians (Complete/CIB) | PS1 | $132.99 | `galerians-ps1-game` | ✅ LIVE |
| 3 | Galerians Ash | PS2 | $32.99 | `galerians-ash-ps2-game` | ✅ LIVE |
| 4 | Mystical Ninja Starring Goemon | N64 | $174.99 | `mystical-ninja-starring-goemon-nintendo-64-game` | ✅ LIVE |
| 5 | Legend of the Mystical Ninja | SNES | $81.20 | `legend-of-the-mystical-ninja-snes-game` | ⚠️ TAG FIX (category:console, should be category:game) |
| 6 | Phantasy Star Online Episode I & II | GameCube | $162.99 | `phantasy-star-online-episode-i-ii-gamecube-game` | ✅ LIVE |
| 7 | Phantasy Star Online Episode I & II Plus | GameCube | $162.99 | `phantasy-star-online-episode-i-ii-plus-gamecube-game` | ✅ LIVE |
| 8 | Phantasy Star Online III: C.A.R.D. Revolution | GameCube | $48.99 | `phantasy-star-online-iii-card-revolution-gamecube-game` | ✅ LIVE |
| 9 | Aidyn Chronicles | N64 | $60.99 | `aidyn-chronicles-nintendo-64-game` | ✅ LIVE |
| 10 | Space Station Silicon Valley | N64 | $108.99 | `space-station-silicon-valley-nintendo-64-game` | ✅ LIVE |
| 11 | Metal Gear Solid | PS1 | $28.99 | `metal-gear-solid-ps1-game` | ✅ LIVE (priced below $30 Winners floor — keep or exclude?) |
| 12 | Silent Hill | PS1 | — | — | ❌ MISSING (Silent Hill Origins PS2 exists but NOT the original 1999 PS1 game) |
| 13 | Silent Hill 2 | PS2 | $175.99 | `silent-hill-2-ps2-game` | ✅ LIVE (near top of price band) |
| 14 | Silent Hill 3 | PS2 | — | — | ❌ MISSING |
| 15 | Fatal Frame | PS2 | $102.99 | `fatal-frame-ps2-game` | ✅ LIVE |
| 16 | Fatal Frame 2 | PS2 | $102.99 | `fatal-frame-2-ps2-game` | ✅ LIVE |
| 17 | Rule of Rose | PS2 | — | — | ❌ MISSING |
| 18 | Haunting Ground | PS2 | — | — | ❌ MISSING |
| 19 | Klonoa: Door to Phantomile | PS1 | — | — | ❌ MISSING (only Klonoa Wii remaster exists at $26.99) |
| 20 | Skies of Arcadia Legends | GameCube | — | — | ❌ MISSING |
| 21 | Custom Robo | GameCube | $54.99 | `custom-robo-gamecube-game` | ✅ LIVE |
| 22 | Geist | GameCube | $37.99 | `geist-gamecube-game` | ✅ LIVE |
| 23 | Baten Kaitos Origins | GameCube | $33.99 | `baten-kaitos-origins-gamecube-game` | ✅ LIVE |
| 24 | Eternal Darkness: Sanity's Requiem | GameCube | $101.99 | `eternal-darkness-gamecube-game` | ✅ LIVE |

**Audit summary (2026-04-11):** 18 LIVE, 1 tag-fix needed, 5 missing from catalog.

### Actions before launch

1. **Fix Legend of the Mystical Ninja tag bug.** ✅ DONE 2026-04-11. `scripts/optimize-product-feed.py:92` (the `get_category()` function) contained a buggy rule `if "system" in pt_lower: return "console"` which miscategorized all 694 products where productType contained "Super Nintendo Entertainment System" etc. Script patched, then `scripts/fix-miscategorized-tags.py` ran across all 694 products and replaced `category:console` with `category:game` (0 errors).

2. **Decide on Metal Gear Solid PS1.** Current price $28.99 is *below* the $30 Winners floor. Options: (a) include it anyway since it's a proven bestseller, (b) raise the price to $34.99 via `scripts/price-sync.py --only-sku 5941 --force-price 34.99`, (c) exclude from Winners and let Discovery campaign cover it.

3. **Source the 5 missing titles** (Silent Hill 1, Silent Hill 3, Rule of Rose, Haunting Ground, Klonoa PS1, Skies of Arcadia Legends) OR drop them from the Winners list. **Decision 2026-04-11: DROP from Phase 1.** Launch with the 17 products already LIVE. Revisit sourcing after the first 14 days of data — if the vibe campaign is working, it's worth the effort to import these. If not, they stay dropped.

4. **Final Phase 1 Winners list — ready for ads:** 17 products (16 unique handles — Galerians Game Only + CIB share a handle). Audited by `scripts/audit-winners-landing-pages.py` on 2026-04-11: **0 blocking issues**. Full report at `docs/winners-landing-page-audit.md`.

### Landing-page quality — recommended (not blocking) fixes

Every Winner has:
- **Only 1 product image.** Google Shopping Quality Score rewards 3+ images. Cowork can shoot a second angle + disc/box-back shots with the Sony A7S III; or we can scrape additional box-art images from PriceCharting via a small script.
- **Missing SEO meta description.** Shopify falls back to truncated body HTML, which is OK but not optimal. A one-line canned pattern like `"Buy {title} for {console} at 8-Bit Legacy — {condition}, fast shipping, 90-day returns."` would lift CTR on Shopping ads and organic search. Low-effort to batch-apply via a script.
- **Missing `mm-google-shopping.custom_product = true`.** Being fixed by `scripts/fix-gtin-metafields.py` in a store-wide sweep (6,105 products). This is what tells Merchant Center to bypass the GTIN requirement for used retro games — without it, products can get disapproved for missing GTIN.

**Pattern:** Every entry is a **cult/niche title on a retro console where the store has variant options (Game Only + CIB)**. Avoids head-to-head with DKOldies/Lukie Games on mainstream mega-hits ("Zelda OoT N64", "Mario 64", "Final Fantasy VII") where:
- Their SEO and reviews beat us
- The Google Shopping auction is expensive
- Conversion rate is lower because buyers comparison-shop

Niche titles are the opposite on every dimension: lower auction cost, higher buyer conviction, less direct price comparison.

## How to load this into Google Ads

**Option A — product groups filter (recommended):**
1. In the `8BL-Shopping-Winners` campaign, create a single ad group
2. Use product groups → subdivide by **Item ID** (Shopify SKU)
3. Manually include only the SKUs from this list
4. Set all others to "Excluded"

**Option B — via a custom label:**
1. Tag all Winners products with a new Shopify tag `ad_group:winners`
2. Re-run `optimize-product-feed.py` (or a new script) to bump these into `custom_label_4`
3. In Google Ads, filter the ad group by `custom_label_4 = winners`
4. Trade-off: requires a script change, but is more maintainable long-term

Recommend Option A for Phase 1 (get live fast), migrate to Option B in Phase 2 if we expand the list beyond 30 products.

## Verification needed before launch

- [ ] Spot-check every product in the list is **in stock** in Shopify (CIB variant purchasable after the 2026-04-06 inventory fix)
- [ ] Spot-check every product has **an image** in the feed (Google Shopping requires)
- [ ] Verify the current live prices match the prices in this doc (prices drift daily via price-sync)
- [ ] Confirm none are in the "Special Products" stale collection
- [ ] Confirm every product has `category:game` in tags (not `accessory` or `console`)
- [ ] Confirm none fall into the sale wave — Winners should run at full price during the first ads window, measure real CVR

## Products to explicitly EXCLUDE from the Winners campaign

Even within retro games, these categories should stay out of the initial campaign:

- **Any Pokemon product** (different campaign strategy — see v2 plan)
- **Any product under $30** (fees + ad cost + dropship margin = likely loss on every sale)
- **Any product over $200** (too much purchase commitment for a cold store with 0 reviews)
- **Consoles and hardware** (higher return rate, higher fraud rate, different buyer intent — own campaign later)
- **Accessories** (controllers, memory cards — low AOV, not the right entry point)
- **Sealed Pokemon products** (different economics, run as own campaign)
- **Recent additions (<30 days old)** (price hasn't stabilized yet)
- **Anything in the "Hands Off" list of sale-wave-plan-april-2026.md** — wait, that's the organic winners, which we DO want. Disregarding.

## Expansion plan (post Phase 1 data)

After 14 days of Phase 1, pull the search terms report:

- Any Winners product with **≥2 conversions** → promote to a scaled-up sub-group
- Any Winners product with **≥20 clicks and 0 conversions** → pause it (remove from the list)
- Any new search term from the `8BL-Shopping-Discovery` campaign that converted → add a matching Shopify product to the Winners list

Target Winners list size after 30 days: 30–50 products.
Target Winners list size after 90 days: whatever maximizes ROAS > 500%, probably 75–150 products.
