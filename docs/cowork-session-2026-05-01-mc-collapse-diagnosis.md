# Cowork Session — 2026-05-01 — MC Collapse Diagnosis

**Surface (urgent, read this first):** The 2 products currently in Feed B (`Shopify App API` / `USD_88038604834` / source ID `10643774057`) are **both variants of the single product "3 Ninjas Kick Back" (Shopify gid `7956600029218`)** — the exact product the pilot `custom_label` metafield was set on the morning of 2026-04-29. Both variants show status = Approved. No other products are in Feed B. This is almost certainly the smoking gun: setting that pilot metafield (or the metafield-definition access scope behind it) flipped the Shopify → MC push to only include products carrying that metafield, and the other ~24,500 products got dropped on the next sync. Verify the metafield definition's access scope and any recent change to the Shopify sales channel "products to sync" filter before doing anything else. **Account is not suspended, all auth is intact** — this is purely a Shopify-side filter / sync issue.

## Verdict

- [x] **Sync collapse: Shopify ↔ MC link broken (most actionable)** — auth intact, feed exists, but Shopify is only pushing 2 of ~7,689 active products. Strong circumstantial evidence ties the collapse to the 4/29 pilot custom_label metafield.
- [ ] Mass disapproval: products synced but MC rejected most (fix at MC/policy level)
- [ ] Account suspension: MC has flagged the account (requires appeal)
- [ ] Feed B deletion: Feed B is missing from Data sources (catastrophic, my fault from 4/29)
- [ ] In-progress propagation: numbers are mid-resync after 4/29 cleanup, will normalize on its own
- [ ] Other

The MC totals (~4K total, 39 Approved, 3.95K Not approved) are misleading — those are NOT Feed B products. They are products **auto-discovered by Google's web crawl** of `8bitlegacy.com` (a separate "Found by Google" data source that began populating after Feed B emptied out). Most of those crawl-discovered products are disapproved because they lack the structured metadata Feed B was supplying. Feed B itself only has 2 items.

## Check 1 — Shopify G&Y app

**Overview tab** (https://admin.shopify.com/store/dpxzef-st/apps/google/overview):
- Connected services → Google Merchant Center: status badge = `Active`
- Total products synced: **2**
- Approved: **2** / Limited: **0** / Not Approved: **0** / Under Review: **0**
- No "Last sync" timestamp surfaced on the overview card
- No red/yellow error banner. Only banner present: a benign "How's your experience with the Google & YouTube app?" feedback prompt
- No "Reconnect" / "Reauthorize" / "Sync error" prompt anywhere
- (Could not access the Marketing methods sub-tab — Shopify embeds the G&Y app in a cross-origin iframe that did not respond to scroll wheel from the cowork browser. Settings page reached via direct link below.)

**Settings → Google services** (https://admin.shopify.com/store/dpxzef-st/apps/google/settings):
- Google Account: `tristanaddi1@gmail.com`
- Connected Google services: **3** — all show a `Disconnect` button (i.e. all 3 are *connected*, none show "Reconnect" / "Disconnected" / "Needs attention")
  - Google Merchant Center: `5296797260` ✓ matches expected
  - Google Ads: `8222102291 (8-Bit Legacy)` ✓ matches expected
  - Google Business Profile: present, connected (full row not captured)

**Conclusion for Check 1:** auth between Shopify and MC is intact. The 2-product number is not an auth/disconnection problem — Shopify is choosing to push only 2 products.

## Check 2 — MC Data sources

URL: https://merchants.google.com/mc/products/sources?a=5296797260

### "Found by Google" (web crawl, primary source NOT controlled by Shopify push)

| Source | Source ID | Type | Feed label | Products | Update freq | Last updated |
|---|---|---|---|---|---|---|
| 8bitlegacy.com | `10430181404` | Web crawl | US | **3,996** | Every 24 hours | (within last 24h, "Update" action button shown) |

This number is incrementing in real time — it was 3,993 at first inspection (~09:30 ET), 3,996 a few minutes later. Google is actively crawling the storefront and ingesting products on its own. **This is the source of the "~4K" total Tristan saw in MC Overview, NOT Feed B.**

### "Provided by you" (3 rows)

| Name | Source ID | Type | Feed label | Products | Last updated |
|---|---|---|---|---|---|
| Content API | `10317468137` | Content API | US | 0 | — |
| Shopify App API | `10587067670` | Merchant API | US | 0 | — |
| **Shopify App API** | **`10643774057`** | **Merchant API** | **`USD_88038604834`** | **2** | **—** |

The third row is the canonical Feed B from `docs/cowork-session-2026-04-29-mc-fix-and-flip.md`. Source ID matches. **Feed exists, is not deleted.** Item count has collapsed from ~24,500 (4/29 12:00 ET) to 2. "Last updated" is `—`, suggesting either MC has no record of a successful push on this feed since the collapse, or the timestamp UI surfaces only when ≥1 push has succeeded recently.

The two `0`-product zombie rows (Content API and the second Shopify App API with feed label `US`) are pre-existing empty placeholders — they appear with `0` items and `—` for last updated. Not new since 4/29.

No red error badges on any data source row.

## Check 3 — MC Overview + Diagnostics

URL: https://merchants.google.com/mc/overview?a=5296797260

**"Your business on Google" widget — Today vs 7 days ago, All marketing methods:**
- Total products: **4K** (delta: **−8.28K**)
- Approved: **39** (+10)
- Limited: **2** (**−12.2K**)
- Not approved: **3.95K** (**+3.94K**, growing — was 3.96K minutes later)
- Under review: **0** (+0)

**Reading this:** 7 days ago (~2026-04-24) the catalog was ~12.2K Limited + ~30 Approved (≈ matches the 4/29 24,984 number partially — possibly because 4/24 was already after a different sync hiccup). Between then and today, ~12.2K Limited products evaporated and ~3.94K new Not-approved products appeared. The 12.2K disappearing is Feed B emptying. The 3.94K appearing is the web-crawl auto-discovery filling the gap with mostly-rejected products (rejected because the crawl-discovered listings lack the curated metadata Feed B previously supplied).

**Store quality (Overview card):** Overall = Great, Delivery time = Fair, Shipping cost = Good. No warning state.

**Banners on Overview:** none indicating suspension, policy violation, sync error, or domain unverification. Only neutral / growth-tip banners.

**"What to do next" / Items requiring attention:**
- GROWTH: "Make fixes so customers can find your products — 3,956 of your products might have missing or inaccurate product details. Review and fix what needs attention." (the 3,956 is the bulk of the 3.95K Not-approved; this is the web-crawl pile)
- TIP: "Top products that drove your performance — 'The Crow City of Angels - PS1 Game Game Only' clicks went against the trend"
- (additional tips: Update descriptions for Nintendo Games / Business Manager / Turn on automatic image improvements / Restock products that are popular on Google / Create custom reports with generative AI / Highlight your best deals / Show your loyalty program benefits / Help shape Merchant Center / Google Wallet — all routine growth tips, none policy-related)

**Diagnostics:** the legacy `/mc/diagnostics` URL no longer exists in the rebranded MC and redirects to Overview. Item-level diagnostics are now surfaced under Products → Needs attention; account-level issues would surface as Overview banners. **None present.**

## Check 4 — MC Notifications + account status

**Notifications** (https://merchants.google.com/mc/taskhub?a=5296797260): 11 cards visible, all GROWTH or TIP category. Verbatim list of card titles:
1. GROWTH — "Make fixes so customers can find your products" (3,956 products)
2. TIP — "Top products that drove your performance"
3. GROWTH — "Update descriptions for Nintendo Games" (346 products)
4. (Business Manager card)
5. TIP — "Turn on automatic image improvements"
6. GROWTH — "Restock products that are popular on Google" (121 Software products)
7. TIP — "Create custom reports with generative AI"
8. GROWTH — "Highlight your best deals and land more sales"
9. GROWTH — "Show your loyalty program benefits on your products"
10. TIP — "Help shape Merchant Center"
11. TIP — "Let your customers add loyalty cards, gift cards, and more to Google Wallet"

**Zero** notifications matching: "Account suspended" / "Policy violation" / "Verification failed" / "Misrepresentation" / "Feed sync failed" / "Authentication issue" / "Domain not claimed" / "Website not verified".

**Settings → Business info** (https://merchants.google.com/mc/merchantprofile/businessinfo?a=5296797260):
- Business name: 8-Bit Legacy
- Business address (Moultrie, Georgia, US — full street redacted from this committed doc)
- Customer service contact: `info@8bitlegacy.com`
- **Online store: `8bitlegacy.com` — `Verified` ✓ `Claimed` ✓**
- Banner: "You're no longer able to manage your business logo and colors" (a generic Google deprecation notice, not an issue with this account)
- No suspension / verification / policy-violation banner anywhere on Business info.

## Check 5 — Cross-vantage comparison table

| Source | Total | Approved | Limited | Not approved | Under review | Last updated |
|---|---|---|---|---|---|---|
| Shopify Admin (raw products, ACTIVE status) | 7,689 | n/a | n/a | n/a | n/a | live (per Tristan, just verified pre-cowork) |
| Shopify G&Y app Overview | **2** | 2 | 0 | 0 | 0 | not surfaced |
| Shopify G&Y feed-level item counts (sub-tab not reachable) | unknown | n/a | n/a | n/a | n/a | unknown |
| MC Overview | 4K (3,996 + 2) | 39 | 2 | 3.95K–3.96K (growing) | 0 | live |
| MC Data sources sum (web crawl 3,996 + Content API 0 + Shopify US 0 + Shopify USD_88038604834 2) | **3,998** | n/a | n/a | n/a | n/a | live |

**Mismatch pattern:**
- Shopify Admin (7,689) ≫ Shopify G&Y app (2) → Shopify is filtering out ≈99.97% of products before pushing to MC. **Locus of failure is Shopify-side, post-Admin, pre-MC.**
- Shopify G&Y app (2) = MC Feed B (2) → the 2 products that *do* get pushed land in MC correctly. Push channel itself is healthy.
- MC Feed B (2) ≪ MC Overview total (4K) → the bulk of MC's catalog is **not** Feed B at all; it's the web crawl auto-discovery that began filling the void. This explains why the 39 Approved / 3.95K Not approved breakdown looks alarming: it's Google trying to crawl the storefront on its own and rejecting most of what it finds for missing structured data.

## Check 6 — Feed B spot-check

URL: https://merchants.google.com/mc/products/sources/detail?a=5296797260&afmDataSourceId=10643774057&tab=settings

**Source details panel:**
- Type: Merchant API
- Content: Products
- Products: **2**
- Last updated: **—**

**About this data source:**
- Source name: Shopify App API
- Source ID: `10643774057` ✓

**How the data will be used:**
- Countries: United States
- Language: English
- Feed label: `USD_88038604834`
- Marketing methods: Free listings, Shopping ads, +3 more

No red error banner, no "Items needing attention" widget on the feed detail page.

**Per-item sample — clicked "2" products link (filter applied: primary_source_info = 10643774057):**

| Visibility | Status | Title | Product ID | Price |
|---|---|---|---|---|
| ✓ active | **Approved** | 3 Ninjas Kick Back - Sega Genesis Game Complete (CIB) | `shopify_ZZ_7956600029218_4379468729 5522` | $97.83 |
| ✓ active | **Approved** | 3 Ninjas Kick Back - Sega Genesis Game Game Only | `shopify_ZZ_7956600029218_4379475270 0450` | $81.99 |

Both products = the two variants (CIB + Game Only) of the same Shopify product `7956600029218`. Per `CLAUDE.md` and the 4/29 brief, gid `7956600029218` is exactly the product where the pilot `custom_label` metafield was applied on the morning of 2026-04-29.

The "Understand your product status changes" chart on the Products page (filtered to source 10643774057) shows the historical product count topping out near 27K and then collapsing — visually consistent with the 24,984 → 2 narrative.

## Anything weird (free-form)

- **Web-crawl auto-discovery is actively masking the problem in MC's headline number.** The 4K MC total is misleading because most of it is auto-crawled, not the curated Shopify push. If/when the auto-crawl is reviewed/disabled, the MC total would drop to 2.
- The "Found by Google" web-crawl product count went from 3,993 → 3,996 in <10 minutes during this session — Google is actively crawling and ingesting from `8bitlegacy.com` right now.
- The two zombie 0-item data sources (Content API at `10317468137` and the second Shopify App API at `10587067670` with feed label `US`) appear to be pre-existing legacy / orphan rows. Worth confirming with Tristan whether these were supposed to be cleaned up at some point — they don't appear to be doing harm but they're noise.
- Total clicks on Google for the 8-Bit Legacy storefront over the last 28 days: 119 (down 30.8%). The performance impact of the catalog collapse is already visible.

## What this means / what to do next (out of scope for this read-only cowork; for Tristan's awareness only)

**Likely root cause hypothesis** (to be validated, not acted on yet):
1. On 2026-04-29 ~10:00, you wrote a `custom_label` metafield value to one product (gid `7956600029218`).
2. The `custom_label` metafield definition's *access* scope (Storefront / Sales channels) likely controls whether products without that metafield are visible to the Google sales channel.
3. After you set the metafield definition (or it was set/auto-created by the Shopify Google & YouTube app on first use), the next sync re-evaluated which products are eligible to push, decided "only products that have a defined value for this metafield are eligible", and dropped the other 24,982 from the feed.
4. The supplemental-feed disaster (4/29 AM) and feed deletion (4/29 PM) may be unrelated symptoms of the same cascade, or independent — but they aren't the cause of the 24,500 → 2 drop. The drop is too clean (exactly the 1 product with the metafield) to be a feed-deletion side effect.

**Verification path (do not execute now — pause for your decision):**
- Inspect Shopify Admin → Settings → Custom data → Products → Metafield definitions, find the `custom_label` definition, check its "Access" tab for "Storefronts" → "Sales channels". If it's restricted, that's the cause.
- Or: Shopify Admin → Sales channels → Google & YouTube → (settings) → product feed eligibility filter. If it has a "products with this metafield" filter, that's the cause.
- Either way the fix is to broaden the eligibility back, NOT to delete or reset Feed B.

**Reminder of the original guardrail:** I did not click any mutation buttons. No feeds were touched, no settings changed, no products edited. The state of MC + Shopify is exactly the same as when this cowork started.
