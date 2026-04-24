# Review-Seeding Email Template — Past Buyers

**Purpose:** seed the first Google Customer Reviews / Shopify Product Reviews on the store before Google Ads launch. Zero reviews on a retro gaming store is the single biggest CVR drag we have — especially comparing against DKOldies (200+ reviews) and Lukie Games.

**Source list:** Shopify admin → Orders → filter `paid AND shipped` → top 5 most recent non-refunded. Grab `first name`, `email`, order # and primary item title.

**Time:** 2 min to look up, ~15 min to personalize + send all 5.

**Expected conversion:** 1-3 of 5 will probably respond. Even 2-3 written reviews on the storefront moves the needle materially vs zero.

---

## Template A — Short, personal (preferred)

**Subject:** Quick ask — how was your {ITEM} from 8-Bit Legacy?

Hey {FIRST_NAME},

Thanks for ordering {ITEM} from us a few weeks back (#{ORDER_NUMBER}) — hope it's been playing well.

Quick ask: would you be up for leaving a short review on 8bitlegacy.com? Even a sentence or two would mean a lot — we're still new and building up credibility, and reviews from real customers go a lot further than anything I can say about the store.

If you've got 60 seconds:
→ https://8bitlegacy.com/products/{PRODUCT_HANDLE}

Thanks either way. Appreciate you taking a chance on a small store.

— Tristan
8-Bit Legacy

---

## Template B — Shorter, more casual (fallback if A feels too formal for the relationship)

**Subject:** How's the {ITEM}?

Hey {FIRST_NAME},

Checking in — did the {ITEM} from 8-Bit Legacy arrive OK and play alright?

If you've got a second and it's been good, a quick review on the product page would help a ton. Still building the store's rep from zero.

→ https://8bitlegacy.com/products/{PRODUCT_HANDLE}

No pressure if you're busy. Just appreciated having you as a customer.

— Tristan

---

## Sending rules

1. **Send one at a time over 20-30 minutes** (not as a batch / bcc). Gmail flags bulk sends, and personalization matters here.
2. **Use your real `tristanaddi1@gmail.com` or the 8-Bit support address** — not a marketing@ or noreply@.
3. **Do NOT include a discount code** — attaching a code turns this into a solicitation and breaks the "sincere ask" vibe. Google Customer Reviews explicitly frowns on incentivized reviews too.
4. **Do NOT send to the Mystical Ninja N64 or Aidyn Chronicles N64 refunded customers** — they didn't receive the item. Filter Shopify orders to `financial_status=paid AND fulfillment_status=shipped` first.
5. If someone replies asking "how?", walk them through: the product page has a review widget at the bottom (Shopify Product Reviews / Google Customer Reviews opt-in fires after purchase).

---

## Scope note

This is a one-time seeding pass, not a recurring campaign. A proper post-purchase review request flow (auto-email 14 days after ship) is a later task per `memory/feedback_email_sequencing.md` — email sequencing is paused until site+social+ads are all live. This template is the manual stop-gap for launch week specifically.
