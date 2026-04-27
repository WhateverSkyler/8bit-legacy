# Cowork Session — 2026-04-27 — MC Audit + Pixel Confirmation

Read-only audit. No products, feeds, settings, or campaigns were modified.

## Task 1A — MC counts

Account: `5296797260` (8-Bit Legacy). Counts captured from Overview ("Today" view) and All Products page.

- **Total products: 25,488** (~25.5K — well below the ~36K estimated in the brief)
- **Approved: 36** (delta vs 7 days ago: +28)
- **Limited: 25.5K** (delta: +13.3K)
- **Disapproved (Not approved): 10** (delta: -28)
- **Pending (Under review): 0** (delta: +0)

Composition on All Products page:
- Provided by you: 25.5K
- More found by Google: 46
- Not showing on Google: 10

**Feeds:**

| Name | Source | Feed label | Source ID | Item count | Last updated |
|---|---|---|---|---|---|
| 8bitlegacy.com (Found by Google) | Auto-discovery | US | — | 46 | Every 24h, Auto |
| Content API | Content API | US | — | 0 | — (empty) |
| Shopify App API | Merchant API | US | — | 0 | — (empty) |
| Shopify App API | Merchant API | **US** | **10633472160** | **12,226** | — (push, not pull) |
| Shopify App API | Merchant API | **USD_88038604834** | **10643774057** | **13,252** | — (push, not pull) |

Math check: 12,226 + 13,252 + 46 = 25,524 ≈ 25.5K total. ✓

**Duplication hypothesis: CONFIRMED — but not the cause originally suspected.**

The duplication is NOT primarily Game Only + CIB variants. It's that **two active Shopify App API feeds** are submitting overlapping product sets to MC:
- Feed 1 (`Source ID 10633472160`, feed label `US`) — 12,226 items
- Feed 2 (`Source ID 10643774057`, feed label `USD_88038604834`) — 13,252 items

Both are configured for Free listings + Shopping ads + 3 more channels. The slight count difference (1,026 items) is likely sync timing or minor scope differences between the two feeds. The `USD_88038604834` label suggests this feed was created when a USD currency-specific feed label was added, but the original `US` feed was never deactivated. **There are also two empty feeds** (Content API, and a third Shopify App API with 0 items) that are inert but cluttering the data sources page.

The brief's "12K Shopify × 2.5 = 30K" theory turned out to be wrong because the actual MC total is 25.5K, not 36K, and the duplication is feed-level, not variant-level. (Variants are still in there, just not as the primary multiplier.)

## Task 1B — Limited products sample

The "Needs attention" diagnostic view shows **only 549 products with fixable data issues** (~2% of the 25.5K Limited total). The other ~24.9K are limited for non-fixable reasons (low historical impressions / "Limited performance" — the standard new-feed MC behavior).

**All 6 fixable issue categories (sum across categories ≈ 548 products, with overlap on a few):**

| Issue | Count | % of total |
|---|---|---|
| Invalid image encoding [image_link] | 418 | 1.6% |
| Personalized advertising: Sexual interests | 51 | <1% |
| Restricted adult content | 51 | <1% |
| Image uses a single color | 16 | <1% |
| Missing value [availability] | 8 | <1% |
| Product page unavailable | 4 | <1% |

**5 sampled Limited products (from the Needs attention table, sorted by the default order):**

| # | Title (50ch) | Variant | Click potential | Status | Issue(s) |
|---|---|---|---|---|---|
| 1 | NASCAR Thunder 2004 - Xbox | Game Only | Low | Limited | Invalid image encoding |
| 2 | Leisure Suit Larry Magna Cum Laude - PS2 | Complete (CIB) | Low | Limited | Missing local inventory data; Personalized advertising: Sexual interests; Restricted adult content |
| 3 | Operation Flashpoint Elite - Xbox | Game Only | Low | Limited | Invalid image encoding |
| 4 | Puzzle Scape - PSP | Complete (CIB) | Low | Limited | Invalid image encoding |
| 5 | Ghosts 'n Goblins - Gameboy Color | Complete (CIB) | Low | Limited | Invalid image encoding |

**Custom labels (over_50 / 20_to_50 / under_20 / game / pokemon-card etc.):** Not visible in MC's Additional details panel for the products inspected. The MC product details page lists `google_product_category`, `item_group_id`, `product_detail`, `product_type`, `sell_on_google_quantity`, `shipping_weight`, `modification info`, but no `custom_label_0` / `custom_label_2` rows. Either the Shopify App API feed isn't submitting them, or MC's UI just doesn't surface them. The "Raw data source attributes: Shopify App API" sub-section was empty when inspected. **Implication for the campaign:** if `custom_label_0=over_50` is what the bid-tier strategy keys on, that label may not actually exist in the MC feed — worth verifying in Shopify before campaign launch.

**Are over_50 tier products disproportionately Limited? UNCLEAR.** Without visible custom_labels in MC, I couldn't filter by tier. The 5-product sample skews CIB-heavy (3 of 5 are CIB variants), but that's a separate finding (see 1C). Click potential for all 5 sampled = "Low" — no relative comparison possible.

The dominant pattern is: **most Limited products are limited because of "low click potential" / new-feed performance constraints, not data issues.** The 549-product fix backlog is small relative to the 25.5K total.

## Task 1C — CIB exclusion verification

**CIB exclusion is NOT working in MC. Verified across multiple SKUs.**

Searched MC for `Final Fantasy VII`. Returned products and their MC status:

| Title | Variant | Price | Status | Visibility |
|---|---|---|---|---|
| Final Fantasy VII Dirge of Cerberus - PS2 Game | Complete (CIB) | $40.99 | **Approved** | ✓ |
| Final Fantasy VII Dirge of Cerberus - PS2 Game | Game Only | $19.99 | **Approved** | ✓ |
| Crisis Core: Final Fantasy VII - PSP Game | Complete (CIB) | $21.99 | **Approved** | ✓ |
| Crisis Core: Final Fantasy VII - PSP Game | Game Only | $14.99 | **Approved** | ✓ |
| Final Fantasy VIII - PS1 Game | Complete (CIB) | $29.99 | **Approved** | ✓ |

Drilled into Leisure Suit Larry CIB product detail (Limited):
- Visibility preference checkboxes: **✅ Show on Google** *and* **✅ Show in ads** — both ON for the CIB variant.
- Marketing methods (full list, after expanding "+2 more"): **Free listings, Shopping ads, Dynamic remarketing, Cloud retail.** All four channels active for this CIB.
- One of its 3 needs-attention issues is "Missing local inventory data," and the fix-text from Google explicitly mentions: *"you can use the [excluded_destination] attribute in your data source to indicate the marketing methods to turn off free_local_listings and local_inventory_ads"* — i.e. exactly the metafield that was supposed to be set on 2026-04-24.

**CIB variants showing "Excluded from Shopping ads" in MC? NO. They appear as Approved (or Limited) with Shopping ads enabled.** The `mm-google-shopping.excluded_destination` metafield set on 2026-04-24 is not propagating to either Shopify App API feed. If the `8BL-Shopping-Games` campaign goes live in this state, CIB variants will compete for ad spend.

## Task 2A — Conversion counts (last 24h / "Today")

Account: `822-210-2291` (8-Bit Legacy). Date filter: `Today / Apr 27, 2026`.

| Action | All conv. | Value |
|---|---|---|
| Google Shopping App Purchase (1) | 0.00 | 0.00 |
| Google Shopping App Add To Cart (1) | 0.00 | 0.00 |
| Google Shopping App Begin Checkout (1) | 0.00 | 0.00 |
| Google Shopping App View Item (1) | 0.00 | 0.00 |
| Google Shopping App Page View (1) | 0.00 | 0.00 |
| Google Shopping App Search (1) | 0.00 | 0.00 |
| Google Shopping App Add Payment Info (1) | 0.00 | 0.00 |

**Total: 0.00 conversions / $0.00 value.** Same numbers when expanded to Apr 1–27 and Last 7 days — the account has zero historical conversions across all 7 actions.

## Task 2B — Webpages tab (Purchase action)

Drilled into `Google Shopping App Purchase (1)` → Webpages tab.

- **Empty.** Message: "You don't have any entries yet"
- URLs seen: **none**
- Earliest timestamp: **n/a**
- Verified across `Today`, `Last 7 days`, and `Apr 1–26, 2026` filters — empty in all of them.

**Important context from the Details tab:** the Purchase conversion action was **created today (Date created: 4/27/2026)**. So part of the "Inactive" tracking status is just because it's brand new — Google hasn't yet seen even one conversion to flip it to "Recording". But order #1071 (placed ~12:30 PM ET, ~3+ hours before this audit) did not produce a webpage entry, which is what we'd expect to see if the Purchase event were firing. The cancellation 5 minutes later may have caused Google to retroactively suppress the conversion, which is one plausible reason for the empty Webpages tab. The other plausible reason is the pixel simply not firing on the thank-you page in the first place. The Webpages tab alone can't distinguish these.

## Task 2C — Tracking status per action

| Action | Tracking status |
|---|---|
| Google Shopping App Purchase (1) | **Inactive** |
| Google Shopping App Add To Cart (1) | **Inactive** |
| Google Shopping App Begin Checkout (1) | **Inactive** |
| Google Shopping App Add Payment Info (1) | **Inactive** |
| Google Shopping App Page View (1) | **No recent conversions** |
| Google Shopping App View Item (1) | **No recent conversions** |
| Google Shopping App Search (1) | **Inactive** |

5 of 7 are "Inactive" — the strongest "broken" state short of "Unverified". 2 of 7 (Page View, View Item) are "No recent conversions" — slightly better, meaning the pipe is set up but no events have been seen recently.

## Anything weird

1. **Account paused banner.** Top of Google Ads UI shows: *"Your account is paused — To run ads again, you'll need to make a payment."* (with a Get started button). This is consistent with the campaign being in draft/paused state, but worth confirming whether billing is set up before the campaign flip.

2. **"Date created: 4/27/2026" on the Purchase conversion action** is the most surprising find. The conversion action itself is brand new today — which means the test order #1071 was the very first opportunity for it to capture a conversion. It didn't. Combined with the empty Webpages tab and "Inactive" status across the board, the most likely interpretation is that the pixel never fired (or fired but Google rejected the event because the action was just minted). Either way, one more uncancelled test purchase would resolve the ambiguity.

3. **CIB exclusion is silently broken.** Memory says all 6,112 CIB variants were excluded on 2026-04-24, but MC shows them as Approved with Shopping ads enabled. The metafield write may have succeeded in Shopify without propagating to MC, or MC sees a different attribute name, or the Shopify App syncs only `excluded_destination` for some channels. This needs a code-level investigation in `scripts/` and the Shopify App API mapping before the campaign can safely flip — otherwise CIB variants will eat ad spend.

4. **Two redundant Shopify App API feeds** with overlapping content (12,226 + 13,252 items) is the actual source of MC bloat, not Game Only/CIB duplication. The `US` feed and the `USD_88038604834` feed should not both be active. Pruning one of them would cut MC inventory roughly in half and likely improve approved-vs-limited ratios since duplicates penalize each other. Two additional empty feeds (Content API + a 0-item Shopify App API) can also be removed.

5. **`custom_label_0` / `custom_label_2` are not visible in MC's product details panel.** If the bidding strategy depends on `custom_label_0=over_50`, this is worth verifying directly in Shopify metafields — the labels may exist in Shopify but not be flowing through the Shopify App API into the MC feed.
