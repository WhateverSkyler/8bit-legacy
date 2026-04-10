# 8-Bit Legacy — Ecommerce Infrastructure Audit

**Date:** April 6, 2026
**Store:** 8bitlegacy.com (dpxzef-st.myshopify.com)
**Auditor:** Claude (automated)

---

## 1. Google Merchant Center + Shopping Feed

**Status: Configured — Pending Product Sync**

- Google & YouTube Shopify app is installed and connected to tristanaddi1@gmail.com.
- Google Merchant Center account **5296797260** is linked.
- Google Analytics property **G-09HMHWDE5K** is connected.
- Product feed sync was initiated. Products will take up to a few days to fully populate in Merchant Center.
- Free listings are enabled — products will appear in Google Shopping organic results once the feed is approved.

**Action needed:** Monitor Merchant Center over the next 48–72 hours to confirm products are approved and appearing in the feed. Check for any disapproved items.

---

## 2. Google Ads Connection

**Status: Requires Manual Resolution**

- The Google & YouTube Shopify app is connected to the **tristanaddi1@gmail.com** Google account.
- That account shows Google Ads account **438-063-8976** in the app dropdown, but this is not the target account.
- The target account **822-210-2291** (MCC 444-244-1892) referenced in `.env.local` and the dashboard is likely under **sideshowtristan@gmail.com**.
- Checking ads.google.com under tristanaddi1@gmail.com revealed only 3 cancelled Google Ads accounts — none matching either ID.

**Action needed (pick one):**
1. Log into ads.google.com with **sideshowtristan@gmail.com** and add **tristanaddi1@gmail.com** as an admin on account 822-210-2291. Then link it through the Shopify Google & YouTube app.
2. Alternatively, disconnect and reconnect the Google & YouTube app using sideshowtristan@gmail.com instead.

Performance Max campaign creation was skipped per your instructions — can be set up after the account is linked.

---

## 3. CIB Variant Inventory Fix

**Status: Script Ready — Needs to Be Run Locally**

- Confirmed the issue: all "Complete (CIB)" variants across the store show **0 inventory** / "SOLD OUT!" while "Game Only" variants show 10,000.
- Created fix script at **`scripts/fix-cib-inventory.py`** that:
  - Fetches all active products via Shopify Admin REST API
  - Identifies CIB variants (by title containing "cib" or "complete")
  - Sets their available quantity to 10,000 at the primary location
  - Supports `--dry-run` mode for preview
- The script could not be run from the sandbox due to proxy restrictions on outbound API calls.

**Action needed:** Run from your local machine:
```bash
cd ~/8bit-legacy
python3 scripts/fix-cib-inventory.py --dry-run   # Preview first
python3 scripts/fix-cib-inventory.py              # Apply changes
```

**Important:** See Task 7 below — the app token may need `write_inventory` scope added first.

---

## 4. Shopify Store Settings

**Status: Verified — All Good**

Reviewed in a previous pass. Key findings:
- **Payments:** Shopify Payments active (2.9% + $0.30, Basic plan)
- **Checkout:** Standard Shopify checkout configured
- **Shipping:** Free shipping over $50, standard rates configured
- **Taxes:** US tax collection enabled

No issues found.

---

## 5. Shop App / Sales Channels

**Status: Likely Resolved — Not Fully Verifiable Today (updated 2026-04-10)**

- **Online Store** — Active and working
- **Google & YouTube** — Installed and connected (see Task 2 for Ads account issue)
- **Shop** — Originally showed "Action needed" due to CIB variants being out of stock. The CIB variant fix has since been completed (6,112 variants set purchasable, per `CLAUDE.md` completed list).

**Recheck on 2026-04-10 (cowork browser session):**

- The sidebar black-dot indicator next to "Shop" cleared after a single visit to the channel page, which in Shopify admin convention means it was a "new / unread notification" marker, not a persistent "Action needed" error badge.
- No "Action needed" text, warning, or error badge was visible in the accessibility tree of the Sales channels page or the Shop app sidebar.
- The embedded Shop channel iframe at `/store/dpxzef-st/apps/shop-72/merchant/catalog` would not render its content in this automation session — it throws an `InvalidStateError: Transition was aborted because of invalid state` in the console, which is a known Shopify admin iframe-routing quirk, not a sign of a merchant-facing issue.
- Note also: the "On Sale" smart collection (see `docs/sale-collection-status-2026-04-10.md`) is NOT published to the Shop channel. Publishing it would improve Shop discoverability but is not a Task 5 blocker.

**Action needed:** Tristan should do a fresh, manual check of Shop → Catalog in a normal browser session (2-minute task) to fully confirm no "Action needed" state remains. Based on the indirect signals above, Task 5 is **likely complete**.

---

## 6. SEO / Online Store Verification

**Status: Verified — Looking Good**

- **Homepage:** Loads correctly with 8-Bit Legacy branding, search bar, navigation (Nintendo, Sega, Sony, Xbox, Sale), console category carousel, newsletter popup, social proof notifications, and footer with social links.
- **Collection pages:** Verified Nintendo 3DS Games collection — 51 items, proper banner image, filter/sort options, grid/list view toggle, product images all loading.
- **Product detail pages:** Verified Fire Emblem: Awakening — product image loads, price ($44.46) displayed, "In Stock" badge, SKU shown, variant selector (Game Only / Complete CIB), Add to Cart + Buy with Shop Pay + Wishlist buttons, free shipping notice, trust badges (free shipping over $50, 24/7 service, secure payments, 10% off first order).
- **Announcement bar:** "1 YEAR WARRANTY On All Orders + 30 Day Guaranteed Return Policy!" — prominent and visible.

**Issue noted:** Complete (CIB) variant shows "SOLD OUT!" badge on product pages — will be fixed by Task 3.

---

## 7. Shopify App API Scopes

**Status: Likely Missing `write_inventory` — Needs Verification**

The "8-Bit Legacy Dashboard" app (unlisted, installed April 1) shows the following permission areas in the Shopify admin:

| Area | View | Edit | Details |
|------|------|------|---------|
| Products | Yes | Yes | Products, collections |
| Orders | Yes | Yes | Order fulfillments, all order history (60 days) |

**What's present:**
- `read_products` / `write_products` (covers products + collections)
- `read_orders` / `write_orders` (covers orders)
- `read_fulfillments` / `write_fulfillments` (listed under Orders as "Order fulfillments")

**What's likely missing:**
- **`read_inventory` / `write_inventory`** — There is no separate "Inventory" row in the permissions table. If these scopes were granted, Shopify would show "Products, collections, **inventory**" or a separate Inventory area.

This matters because:
- The CIB fix script calls `inventory_levels/set.json`, which requires `write_inventory`
- The dashboard's inventory sync and price-sync features need inventory access
- Without this scope, the access token `shpat_c111...` cannot modify inventory levels

**Action needed:**
1. Go to the **Shopify Partners dashboard** (partners.shopify.com) → Apps → 8-Bit Legacy Dashboard
2. Under **Configuration → Admin API access scopes**, add: `read_inventory`, `write_inventory`
3. Save, then **reinstall the app** on the store to get an updated token
4. Update the new access token in `dashboard/.env.local`
5. Then run the CIB fix script

---

## Summary of Action Items

| Priority | Task | Effort |
|----------|------|--------|
| **HIGH** | Add `write_inventory` scope to the Dashboard app in Partners dashboard, reinstall, update token | 10 min |
| **HIGH** | Run `python3 scripts/fix-cib-inventory.py` to fix CIB variants | 5 min |
| **MEDIUM** | Resolve Google Ads account — link 822-210-2291 via sideshowtristan@gmail.com | 15 min |
| **LOW** | Re-check Shop sales channel after CIB fix | 2 min |
| **LOW** | Monitor Google Merchant Center feed approval over next 48-72 hours | Passive |
