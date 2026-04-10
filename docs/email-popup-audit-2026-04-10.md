# Email Popup Audit — 2026-04-10

**Auditor:** Claude (cowork / browser session)
**Scope:** Verify where 10% off newsletter popup subscribers go, whether the welcome flow is firing, and whether the discount code is valid.
**Tied to brief:** `docs/claude-cowork-brief-mac-2026-04-10-pm.md` Task A

---

## TL;DR

The popup is a **hard revenue leak**. Subscribers collect but never receive the 10% code. Every visitor who has entered an email for the past year has been told they'd get a discount and got nothing back — no welcome email, no code, no follow-up.

Three things are true at once:

1. The popup is **theme-native** — it is NOT powered by Klaviyo, Mailchimp, Privy, SmartrMail, or Sumo. It posts directly to Shopify's `/contact` endpoint and creates plain Customer records tagged `newsletter`.
2. **MailMunch** ("Mailchimp Forms" app) is installed and is syncing those customers — it shows **853 subscribers** — but MailMunch's own campaigns are `Inactive` with 0 sends, and MailMunch coupons are a premium-only feature that this account doesn't have.
3. **Zero emails have ever been sent to any of the 853 subscribers.** `Last Contacted` is blank for all of them. No autoresponder exists in MailMunch, and no Shopify Email welcome flow is configured.

The popup copy promises "10% off their first order simply by joining our monthly newsletter" but the customer never sees a code. Unrecoverable abandonment rate on the popup is 100%.

---

## How the popup works (end-to-end)

The popup is hardcoded in the Shopify theme (`bs_newletter_oca_popup` class on a `<div id="newsletter-wrappers">`). It contains a form with:

- `form_type = customer`
- `contact[tags] = newsletter`
- Email field: `contact[email]`
- `action = /contact`

When a visitor submits, Shopify creates a new Customer record tagged `newsletter` and redirects. There is no `thank_you_message` block in the DOM and no code is displayed after submission. There is no JavaScript that calls any third-party email service.

MailMunch ("Mailchimp Forms") is installed on the store and has OAuth access to the customer list, so it picks those new customers up within minutes — that is the only reason MailMunch shows 853 contacts. It is NOT the source of the popup.

---

## MailMunch state (inspected in the MailMunch dashboard)

- Subscribers: **853 total**
- `Last Contacted`: **blank for every contact**
- Campaign "Newsletter Popup May 2025": **Inactive**, 0 contacts, 0 sends
- Autoresponders: **none configured**
- Broadcasts: **none sent**
- Coupons: **locked behind premium plan** (the page explicitly says coupons are a paid feature)

MailMunch is effectively a dead mirror of the Shopify customer list. It is not sending anything and cannot deliver a coupon code even if it wanted to.

---

## Relevant Shopify discount codes (inspected in Shopify → Discounts)

| Code | Status | Uses | Likely purpose |
|---|---|---|---|
| `8BITNEW` | Active | 4 | Most likely the intended popup welcome code |
| `SHOPAGAINFOR10` | Active | 2 | Returning customer 10% |
| `SHOPEXTRA10` | **Expired** | — | Old popup code, still lingering |
| `LUNCHBOX` | Active | 0 | GameCube 10% sale code (referenced in hero banner) |

`8BITNEW` has only 4 uses. Against 853 subscribers that is a **0.47% redemption rate**. Given that the popup delivers no code to the subscriber, the 4 uses are almost certainly people who found the code elsewhere (Reddit, a shared screenshot, or manually guessed).

---

## Findings

- **The popup is a lossy funnel.** 853 emails collected, 0 welcome emails sent, effectively 0 coupon redemptions attributable to the popup.
- **No owned email channel exists.** The "list" is 853 plain Shopify customer records tagged `newsletter`. There is no sending infrastructure — not MailMunch's free tier, not Shopify Email, not Klaviyo, not Mailchimp.
- **The discount-code side is healthy enough.** `8BITNEW` is active and reusable. The code isn't the bottleneck — delivery is.
- **MailMunch is the wrong tool for the job on the free tier.** Coupons are gated behind a paid upgrade, and the app's own campaigns are Inactive.

---

## Recommended action items (ranked by impact/effort)

1. **Highest leverage — free, fast fix.** Install **Shopify Email** (free for up to 10k sends/month on Basic) and build a two-step Welcome Flow:
   - Trigger: `Customer tagged newsletter`
   - Email 1 (immediate): "Welcome to 8-Bit Legacy — here's your 10% off code: `8BITNEW`"
   - Email 2 (+3 days): Curated set of deals (tie to Deals of the Week smart collection)
   - Manually batch-send the welcome email to the existing 853 subscribers first so the historical list is not wasted.

2. **Medium-term.** Evaluate Klaviyo Free (up to 250 contacts) vs Shopify Email. Klaviyo has much better segmentation for a store with 7,290+ products but the free tier is smaller than the existing list.

3. **Clean up MailMunch.** Either upgrade it to a plan that unlocks coupons and configure a real autoresponder, or uninstall it to stop the confusing "Mailchimp Forms" app from sitting in the app list doing nothing.

4. **Delete `SHOPEXTRA10`.** It is expired and cluttering the discount list.

5. **Swap the popup submit path.** Once Shopify Email (or Klaviyo) is wired up, the popup form can keep posting to `/contact` — the customer tag `newsletter` is the trigger — so **no theme edit is required** if we take option 1.

---

## What I did NOT do (per the brief's guardrails)

- Did not modify any MailMunch settings
- Did not send any test email to the real list
- Did not delete subscriber data
- Did not reset, expire, or edit any discount code
- Did not edit the theme

---

## Sources

- Shopify admin → Customers (filtered by tag `newsletter`)
- Shopify admin → Discounts (checked active and expired codes)
- MailMunch dashboard → Subscribers, Campaigns, Autoresponders, Coupons (inspected in browser)
- 8bitlegacy.com homepage DOM (inspected the popup markup directly)
