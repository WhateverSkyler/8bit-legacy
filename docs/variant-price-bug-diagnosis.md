# Variant Price Display Bug — Diagnosis & Fix

**Date:** 2026-04-13  
**Priority:** CRITICAL — #1 conversion lever  
**Status:** Root cause confirmed, fix verified via live DOM injection  

## Bug Description

When customers toggle between variant options (e.g., "Game Only" ↔ "Complete (CIB)"), the displayed price does NOT update. The URL updates (variant ID changes), the hidden form select updates, but the visible price stays locked to whatever it was on page load.

**Impact:** Customers see the wrong price for the variant they're about to buy. CIB variants are typically 2-3x more expensive than Game Only. This silently kills conversions — either customers abandon (wrong price confusion) or they buy CIB thinking it costs the Game Only price.

## Root Cause

**One missing CSS class.**

The theme's variant change callback (`original_selectCallback` in `variants.js`) uses this jQuery selector to find and update the price element:

```js
jQuery('.product-single .product-price__price span.money')
```

But the Liquid template renders the price span **without** the `money` class:

```html
<!-- ACTUAL (broken) -->
<span id="ProductPrice-template--23583179931682__main" itemprop="price" content="162.99">
  $162.99
</span>
```

The selector `span.money` fails because there's no `money` class → price never updates.

## The Fix (1 line)

Add `class="money"` to the ProductPrice span in the Liquid template.

```html
<!-- FIXED -->
<span id="ProductPrice-template--23583179931682__main" class="money" itemprop="price" content="162.99">
  $162.99
</span>
```

### How to apply manually

1. **Duplicate the live theme first** — Shopify admin → Online Store → Themes → ⋯ → Duplicate
2. Open the **duplicate** theme's code editor → ⋯ → Edit code
3. Search all files for `ProductPrice` (likely in `sections/product-template.liquid` or `snippets/product-price.liquid`)
4. Find the `<span>` with `id="ProductPrice-{{ section.id }}"` (or similar)
5. Add `class="money"` to that span
6. Save → Preview the duplicate → Test variant switching
7. If working, publish the duplicate as the live theme

### How to apply via script

```bash
# Preview what will change
python3 scripts/fix-variant-price-display.py --dry-run

# Apply the fix (after manually duplicating theme in admin)
python3 scripts/fix-variant-price-display.py --live
```

## Verification

After applying the fix, test these products:

1. [Phantasy Star Online Episode I & II](https://8bitlegacy.com/products/phantasy-star-online-episode-i-ii-gamecube-game) — Game Only: $162.99, CIB: $303.99
2. Pick 2-3 random multi-variant products from different consoles
3. Toggle variants — price should update instantly
4. Verify the Add to Cart button price/text also updates (availability check)

## Technical Details

### Variant Change Flow (jQuery theme)

```
Radio button click
  → jQuery change handler fires
  → Gets option value from radio
  → Sets .single-option-selector <select> value
  → Triggers 'change' on the <select>
  → Shopify.OptionSelectors bound callback fires
  → selectCallback() → original_selectCallback(variant, selector)
  → jQuery('.product-single .product-price__price span.money').html(Shopify.formatMoney(variant.price))
  ↑ THIS SELECTOR FAILS — no span.money in DOM
```

### DOM Structure

```
SECTION.product-single                          ← .product-single ✓
  DIV.product-page-info
    DIV.product__info-container
      DIV.clearfix.product-price
        P.price-box.product-single__price-...
          SPAN.product-price__price.price        ← .product-price__price ✓
            SPAN#ProductPrice-template--...       ← NO .money class ✗
              $162.99
```

### Files Involved

- `assets/variants.js` — Theme's variant selector initialization (Shopify.OptionSelectors)
- `original_selectCallback` — The price update function (2504 chars, works correctly)
- `selectCallback` — Currency wrapper that calls original_selectCallback
- Product template Liquid file (exact path TBD — search for `ProductPrice` in theme code)

### Why This Broke

The theme likely used a different template at some point that included `class="money"` on price spans (common in currency converter themes). At some point the template was updated/swapped but the new template omitted the `money` class, while the JS callback still targets it.
