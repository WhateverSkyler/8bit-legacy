# Cowork Brief — 2026-05-01 — MC Count Read-Only Check

## Goal

Single read-only check: navigate to the Shopify Google & YouTube app Overview page and report the "Total products synced" number. That's it.

Context: at 15:12 ET I bulk-tagged all 7,142 ACTIVE Shopify products via Admin API, which fired 7,142 products/update webhooks. Now ~20 min later, want to see if the G&Y channel app has processed those webhooks and pushed products back to MC.

Time budget: 90 seconds total.

## Hard guardrails

✗ Do NOT click any button. Read-only.
✗ Do NOT open Settings, Manage products, or any sub-page. Just Overview.
✗ Do NOT touch any pixel, Customer Events, app pixels, custom pixels.
✗ Do NOT touch the Google Ads account or campaign.
✗ Do NOT reconnect/disconnect anything.

If a screen has any clickable button highlighted in a way that suggests "click me to fix" — ignore it. We're observing only.

## Steps

1. Navigate to: `https://admin.shopify.com/store/dpxzef-st/apps/google/overview`
2. Wait for the page to render (the Google Merchant Center card should be visible)
3. Screenshot or capture verbatim:
   - The number labeled "Total products" or "Total products synced" or just the big number on the GMC card
   - The breakdown: Approved / Limited / Not Approved / Under Review (whatever is shown)
   - Any banner / status badge / "Last sync" timestamp visible on the page
   - Any error or "Reconnect" prompts (should be NONE)

## Handoff

Write `docs/cowork-session-2026-05-01-mc-count-check.md` with:

```markdown
# Cowork Session — 2026-05-01 — MC Count Check

## Captured at
<timestamp ET>

## G&Y Overview verbatim
- Total products: ___
- Approved: ___
- Limited: ___
- Not Approved: ___
- Under Review: ___
- Last sync timestamp (if shown): ___

## Status badges / banners
<verbatim>

## Anything weird
<verbatim>
```

That's it. No clicks, no recommendations, no follow-up. Just the number.
