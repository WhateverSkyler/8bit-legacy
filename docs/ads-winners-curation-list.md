# Google Ads — Phase 1 "Winners" Curation List

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

## The List (~24 products, start here)

| # | Title | Console | Price | Why included |
|---|---|---|---|---|
| 1 | Galerians (Game Only) | PS1 | $59.99 | Organic winner. PS1 survival horror cult classic. Low auction competition. |
| 2 | Galerians (CIB) | PS1 | $132.99 | Same franchise, higher-ticket variant for collector intent. |
| 3 | Galerians Ash | PS2 | $32.99 | Sequel — "if you liked X" cross-sell target. |
| 4 | Mystical Ninja Starring Goemon | N64 | $174.99 | Organic winner. Top of the Winners pricing band. One sale = 300+ clicks paid for. |
| 5 | Legend of the Mystical Ninja | SNES | $81.20 | Companion title, proven organic interest. |
| 6 | Phantasy Star Online Episode I & II | GameCube | $162.99 | Organic winner. Extreme collector affinity (servers shut down, cult following). |
| 7 | Phantasy Star Online Episode I & II Plus | GameCube | $162.99 | Rare "Plus" variant = even higher collector intent. |
| 8 | Phantasy Star Online III: C.A.R.D. Revolution | GameCube | $48.99 | Series fan cross-sell. Mid-ticket. |
| 9 | Aidyn Chronicles: The First Mage | N64 | (TBD — verify) | Organic winner per CLAUDE.md notes. Rare N64 RPG. |
| 10 | Space Station Silicon Valley | N64 | (TBD — verify) | Organic winner per CLAUDE.md notes. DMA Design cult classic. |
| 11 | Metal Gear Solid | PS1 | (TBD — verify current price) | Top-3 bestseller per profit-report history. Proven demand. |
| 12 | Silent Hill | PS1 | (TBD — verify) | Iconic survival horror. In the same niche as Galerians. |
| 13 | Silent Hill 2 | PS2 | (TBD — verify) | Franchise cross-sell. |
| 14 | Silent Hill 3 | PS2 | (TBD — verify) | Franchise cross-sell. |
| 15 | Fatal Frame | PS2 | (TBD — verify) | Survival horror niche. High collector affinity. |
| 16 | Fatal Frame II: Crimson Butterfly | PS2 | (TBD — verify) | Franchise cross-sell. |
| 17 | Rule of Rose | PS2 | (TBD — verify) | Rare survival horror, high collector value. |
| 18 | Haunting Ground | PS2 | (TBD — verify) | Rare survival horror, Capcom cult. |
| 19 | Klonoa: Door to Phantomile | PS1 | (TBD — verify) | Cult platformer, enthusiast demand. |
| 20 | Skies of Arcadia Legends | GameCube | (TBD — verify) | Cult JRPG, proven collector demand. |
| 21 | Custom Robo | GameCube | (TBD — verify) | Cult mech-battler, low competition. |
| 22 | Geist | GameCube | (TBD — verify) | Rare Nintendo FPS, collector appeal. |
| 23 | Baten Kaitos Origins | GameCube | (TBD — verify) | Cult JRPG sequel. |
| 24 | Eternal Darkness: Sanity's Requiem | GameCube | (TBD — verify) | Nintendo-exclusive horror, proven enthusiast demand. |

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
