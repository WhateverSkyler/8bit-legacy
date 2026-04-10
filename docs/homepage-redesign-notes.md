# Homepage Redesign Notes — Below "Deals of the Week"

**Date:** 2026-04-10
**Auditor:** Claude (cowork / browser session)
**Scope:** Document visual/UX issues on `https://8bitlegacy.com/` in every section BELOW "Deals of the Week". Do not apply changes — propose them, rank them, wait for Tristan's approval.
**Brand anchors (must honor):** orange `#ff9526`, sky-blue `#0EA5E9`, Nunito font, light theme only, Nintendo Switch-clean aesthetic.
**Tied to brief:** `docs/claude-cowork-brief-mac-2026-04-10-pm.md` Task D

---

## Section map (current homepage, scroll order)

Inspected via DOM (theme `8bit-legacy` aka Shopify theme id `23583179538466`):

| # | Section ID (theme section key) | What it is | Height (px) | Notes |
|---|---|---|---|---|
| 0 | `shopify-section-header` | Announcement bar + nav | 248 | Above the fold, not in scope |
| 1 | `dfddd41c-ce25-4a47-a869-51eca9da24f5` | Hero slideshow (3 slides: NES / Sega / GameCube) | 327 | Above DotW, not in scope |
| 2 | `843fc4da-aabd-4c3a-bc4b-74e23d9dd8a2` | Platform icon row (NES, SNES, N64, GameCube, Wii, Wii U) | 231 | Above DotW, not in scope |
| 3 | `bs_countdown_product_U86wLm` | **Deals of the Week** (countdown + 5 tiles with –7% to –55% badges) | 639 | Cut-off — everything below this is in scope |
| 4 | `bs_banner_three_image_cxQzxU` | "Three image banner" theme section | **0** | 🔴 **EMPTY** — no images configured, renders nothing but vertical whitespace |
| 5 | `bs_cate_product_mGqywb` | **Shop Everything GameCube** — Games / Consoles / Accessories category tiles + 8 product cards | 649 | Works, but under-stocked (8 products vs 20 in Classics sections) and GameCube-only is a weird choice |
| 6 | `bs_banner_three_image_nX4pqz` | "Three image banner" theme section | **0** | 🔴 **EMPTY** — second unpopulated banner slot |
| 7 | `f0e5bec2-56db-481b-b966-847b999513af` | **Nintendo Classics** — 20-tile product grid | 642 | Works; title is 40px Nunito 800 |
| 8 | `bs_grid_product_xweGDQ` | **Sony Classics** — 20-tile product grid | 756 | Works; title is 40px Nunito 800 |
| 9 | `shopify-section-footer` | Footer | 679 | Out of scope |

**The "half-finished" feeling Tristan described is mostly real, and most of it comes from four root causes (see next section).**

---

## Issues identified (ranked by impact ÷ effort)

### Issue 1 — TWO empty "three image banner" sections break the flow (🔴 high-impact, tiny effort)

There are two banner sections in the theme (`bs_banner_three_image_cxQzxU` and `bs_banner_three_image_nX4pqz`) that render with **zero height, zero images, and only an empty `<div class="banner-images-three">` wrapper**. These are placeholder banner sections that were never populated with actual banner images.

Their effect on the page: they split "Deals of the Week → GameCube" and "GameCube → Nintendo Classics" with awkward near-empty gaps. Visually, the homepage feels like there are "missing" sections between the working ones — which is literally what is happening.

**Fix options:**

- **Option A (fastest — 5 min):** Delete both empty banner sections from the theme customizer. The homepage collapses cleanly: Deals of the Week → GameCube → Nintendo Classics → Sony Classics → Footer.
- **Option B (higher impact — 30-60 min):** Populate them. Banner 1 becomes a **Pokemon TCG hero** ("1,176+ singles priced at market, shop all sets") pointing to `/collections/pokemon-cards`. Banner 2 becomes a **Sale** banner pointing to `/collections/on-sale` (the smart collection verified in Task B).
- **Recommendation:** Option A first (free, immediate win), then Option B later when you have banner artwork ready.

**Impact:** High — this is the single biggest contributor to the "half-assed" look.
**Effort:** Tiny (delete) or Small (populate).

---

### Issue 2 — The store's second-biggest product line (Pokemon cards) gets zero homepage real estate (🔴 high-impact, small effort)

Pokemon cards are 1,176+ live products and a major pillar of the catalog per `CLAUDE.md`. The homepage below Deals of the Week features:

- GameCube category tiles
- Nintendo Classics grid
- Sony Classics grid

Pokemon is entirely absent. There is no Pokemon hero slide, no Pokemon category tile, no Pokemon product grid. The only place Pokemon appears in the homepage header area is a single "Trading Cards" nav item in the top menu. A visitor scrolling the homepage would have no idea Pokemon is a meaningful product line on this store.

**Fix:**

- Add a "Pokemon TCG — Singles, Sealed & ETBs" product grid section below Sony Classics. Use the theme's existing `bs_grid_product` or `featured-collection` section tied to the `/collections/pokemon-cards` collection. 8–12 products.
- **OR** repurpose one of the empty banners in Issue 1 as a Pokemon hero.
- **OR** add Pokemon as a fourth hero slideshow slide at the top (also out of scope of "below DotW" but worth noting).

**Impact:** High — Pokemon is a growth lever with full price feed already working. Exposing it on the homepage is free conversion.
**Effort:** Small (15 min in customizer if using an existing product grid section).

---

### Issue 3 — GameCube category section is thin and genre-locked (🟡 medium-impact, small effort)

The "Shop Everything GameCube" section has:

- Three category tiles: Games / Consoles / Accessories — all at 48×48 thumbnails
- Only **8 product cards** rendered, vs 20 in each of the Classics sections below it

The section is visually shorter and less dense than everything around it, making it feel like a downgrade. It also implicitly tells the visitor "we are a GameCube store" — which is not true for a store with 7,290+ products across NES, SNES, N64, GameCube, PS1, PS2, Dreamcast, Saturn, GBA, and Pokemon.

**Fix options:**

- **Option A:** Rename the section to "Shop by Platform" and convert it to a Wii/Wii U/Switch/GameCube/N64/PS2 platform grid using the same `cat-name` card style (the category tiles already exist).
- **Option B:** Keep it GameCube-themed but bump the product count to 20 (to match Classics sections) so it doesn't look half-loaded.
- **Option C:** Tie it to the current sale promo ("All GameCube Games 10% off with LUNCHBOX" is what the hero carousel says) — rename to "GameCube 10% Off Sale" so the section earns its homepage spot.

**Recommendation:** Option C is the most coherent — it ties the hero banner's LUNCHBOX promo to a real landing strip below the fold.

**Impact:** Medium — tightens brand message.
**Effort:** Small (15-20 min theme customizer tweaks).

---

### Issue 4 — No sale/promo strip anywhere below Deals of the Week (🟡 medium-impact, small effort)

"Deals of the Week" handles 5 countdown deals. Then the homepage shows GameCube → Nintendo → Sony product grids with no visual reinforcement of the ongoing sale. The "On Sale" smart collection (483677044770) has 15 products in it — none of them appear on the homepage outside DotW.

**Fix:**

- Add a dedicated "Ongoing Sales" section (use an existing `bs_grid_product` or `featured-collection` section type) bound to the `/collections/on-sale` smart collection. 8-12 products.
- Place it between GameCube and Nintendo Classics to break up the back-to-back grids.
- Pair with the Issue 1 "populate banner 2" fix: the banner becomes a clickable "View All Sales →" CTA that leads into the product strip.

**Impact:** Medium — reinforces ongoing sale without needing new imagery.
**Effort:** Small.

---

### Issue 5 — Hero carousel slides have empty alt text and no link text (🟢 low-impact accessibility fix, tiny effort)

(This is technically above "Deals of the Week" but flagging it because it's cheap and Tristan asked for unrelated cleanups in the same session — ignore if you want to stay strictly below DotW.)

All three hero slides (`nes_banner.png`, `sega_V2.png`, `gc_banner.png`) render with `alt=""` and their anchors have empty visible text. This hurts:

- SEO (Google can't understand what the hero is advertising)
- Screen reader accessibility
- Alt-image search visibility

**Fix:** Add `alt` attributes in the theme customizer (slide 1: "Shop NES Games — 8-Bit Legacy", etc.) and make sure each slide has a visible `Shop Now` CTA button.

**Impact:** Low-medium for SEO, low for UX.
**Effort:** Tiny.

---

## Things that are NOT broken (don't touch)

- Typography is consistent across sections: **Nunito** is used everywhere (verified via computed-style inspection). Section titles are 40px weight 800, category titles 26px weight 700, product titles 16px weight 800, prices 20px weight 800.
- No broken images, no missing alt on product tiles, no $0.00 prices in any visible product grid below Deals of the Week.
- No "negative discount" badges on homepage — the compare_at bug the terminal session is tracking does not surface in homepage tiles (it's limited to deep collection pages).
- Light theme everywhere, no dark sections, no conflicts with the Nintendo Switch aesthetic.
- Sale percentage badges on Deals of the Week (-7%, -55%, -20%, -35%, -44%, -17%, -21%, -50%, -31%, -19%, -13%, -20%, -33%, -16%, -17%) all render correctly with the orange brand color.

---

## Recommended execution order

If Tristan approves, apply in this order (all reversible in the Shopify theme customizer, requires a duplicated theme per the brief):

1. **Issue 1 Option A** — Delete the two empty banner sections. (5 min, highest impact-to-effort ratio.)
2. **Issue 2** — Add a Pokemon TCG product grid below Sony Classics. (15 min.)
3. **Issue 4** — Add an "Ongoing Sales" product strip between GameCube and Nintendo Classics, bound to `/collections/on-sale`. (15 min.)
4. **Issue 3 Option C** — Rename GameCube section to match the LUNCHBOX hero promo and bump product count to 20. (15 min.)
5. **Issue 5** — Add alt text to hero slides. (5 min.)

Total: ~55 minutes. All changes happen in `Online Store → Themes → Customize` on a **duplicated theme**. Preview on mobile and desktop. Nothing gets published until Tristan explicitly approves.

---

## Questions for Tristan

1. Do you want me to delete the empty banner sections, or do you already have Pokemon/sale banner artwork you want to drop into them?
2. Is the LUNCHBOX GameCube sale still running, or should I find a different anchor for the GameCube section?
3. Should I duplicate the theme now so we have a safe staging copy before applying any of this? (I will NOT touch the live theme without your go-ahead.)

---

## What I did NOT do

- Did not make any theme changes
- Did not duplicate the theme
- Did not modify the live homepage
- Did not change brand colors, fonts, or section order
- Did not touch any section above "Deals of the Week"
