# Sale Collection Status — 2026-04-10

**Auditor:** Claude (cowork / browser session)
**Tied to brief:** `docs/claude-cowork-brief-mac-2026-04-10-pm.md` Task B
**Scope:** Confirm the "Sale" smart collection exists, has the right rule, is in the nav, and is in the Merchant Center / Google Shopping feed.

---

## Summary

The smart collection exists and is structurally correct, but there are **two minor cleanup items**: the collection is not published to the Shop sales channel, and the main nav has two "Sale" links pointing at two different collections.

---

## Findings

### Collection exists: "On Sale"

- Collection name: **On Sale**
- Collection ID: `483677044770`
- Type: **Smart** collection
- Rule: **"Compare-at price is not empty"** (equivalent to `compare_at_price > 0`) — this is the correct rule for the sale-wave plan.
- Products currently in the collection: **15**
- Handle: `on-sale`

### Publishing status (Shopify admin → Collection → Publishing)

- Published to: Online Store, Point of Sale, Facebook & Instagram, TikTok, and two other channels.
- **NOT published** to the **Shop** sales channel (white dot in the publishing panel).
- The Merchant Center feed is driven by the Google & YouTube app sales channel, which IS enabled on this collection.

### Navigation menu

The main nav contains **two "Sale" links**:

| Label | Destination |
|---|---|
| Sale | `/collections/special-products` |
| Sale | `/collections/on-sale` |

The `special-products` link appears to be a legacy pointer from an older sale strategy. The new smart-collection link is `/collections/on-sale`. Both render in the main nav simultaneously.

---

## Action items (do NOT auto-apply — ask Tristan)

1. **Remove the duplicate "Sale" nav item.** Delete the `/collections/special-products` menu entry from `Online Store → Navigation → Main menu` and leave only `/collections/on-sale`.

2. **Publish "On Sale" to the Shop sales channel.** Collection → Publishing → enable Shop. This makes the collection discoverable inside the Shop app and Shopify's Shop channel search — useful once Shop-app discovery issues from Task 5 are resolved.

3. **No need to create the collection.** It already exists and the rule is correct for the April sale-wave plan. The only prerequisite missing is populating it with discounted products, which the terminal session's `manage-sales.py` work will handle.

---

## Stale UI warning

The Shopify admin shows a stale banner on the collection that says: *"To add this collection to your online store's navigation, you need to update your menu."* The nav menu actually already has the link (two of them, in fact). The warning is cosmetic / cached and can be ignored. Clicking into Navigation and re-saving the menu will clear it.

---

## What I did NOT do

- Did not modify the smart collection rule
- Did not change publishing channels
- Did not edit the nav menu
- Did not create a new collection (it already exists)
