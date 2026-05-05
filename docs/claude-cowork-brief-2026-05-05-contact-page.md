# Cowork Brief — 2026-05-05 — Create `/pages/contact`

## Goal

Create a simple Contact page in Shopify Admin so the existing footer link `/pages/contact` stops 404'ing. This is gating the Google Ads launch — Google Merchant Center policy requires accessible customer service contact info.

Time budget: ~5 minutes.

## Hard guardrails — read first

✗ Do NOT modify any existing page, theme, navigation, or app
✗ Do NOT install any new app or change theme settings
✗ Do NOT add a Shopify built-in contact FORM with captcha integration unless it's the trivial default — keep it simple
✗ Do NOT touch the footer markup, theme code, or any other page
✗ Do NOT log in for Tristan — surface login walls if hit
✗ Do NOT modify Pages other than the new Contact page
✗ Do NOT enable comments or password protection on the page

If a confirmation dialog says "Are you sure?" in any unexpected context — screenshot, click Cancel, surface back to Tristan.

## Phase 1 — Navigate (1 min)

URL: `https://admin.shopify.com/store/dpxzef-st/pages`

Capture verbatim:
- Page title (should be "Pages" or similar)
- Whether a page named "Contact" already exists in the list (it almost certainly doesn't, since the public URL 404s — but check)
- The "Add page" button (top right typically) — confirm it's visible

If a page named "Contact" already exists:
- Open it, capture the current state, surface back to Tristan. Do NOT modify the existing page. Stop.

## Phase 2 — Create the page (3 min)

Click **Add page**. Fill in:

**Title:**
```
Contact
```

(Shopify auto-generates the URL `/pages/contact` from the title — verify this in the URL handle field, which should appear below or in the right sidebar after typing the title. If the handle defaults to anything other than `contact`, manually override it to `contact`.)

**Content / body** — paste this exact markdown/text (or use the rich-text editor equivalent):

```
# Contact 8-Bit Legacy

We're here to help with any questions about your retro games, Pokemon cards, or order.

**Email:** support@8bitlegacy.com
**Phone:** (229) 329-2327
**Hours:** Monday – Friday, 9 AM – 5 PM Eastern Time

For order-related questions, please include your order number in your message and we'll get back to you within one business day.

Returns and warranty information is available on our [Shipping, Returns & Warranty Policy](/pages/shipping-returns-warranty-policy) page.
```

**Visibility:** **Visible** (the default — leave it as Visible, not Hidden or Scheduled)

**Search engine listing preview / SEO meta** — leave the auto-generated values; do NOT manually edit unless the auto values are completely missing.

**Theme template:** leave the default `page` template selected. Do NOT change to any custom template.

## Phase 3 — Save (1 min)

Click **Save** (top right typically, or bottom of page depending on Shopify UI version).

Wait for confirmation toast (typically "Page created" or "Page saved").

Capture:
- Timestamp at click of Save
- Verbatim text of confirmation toast
- The final URL of the page in the address bar (should look like `https://admin.shopify.com/store/dpxzef-st/pages/<numeric-id>`)
- The "View" / "Preview" link if visible — copy it

## Phase 4 — Verify public URL works (1 min)

Open a new tab and load:
```
https://8bitlegacy.com/pages/contact
```

Capture:
- HTTP response status (open DevTools Network tab if needed, or just confirm the page renders content rather than a 404)
- Whether the page heading reads "Contact 8-Bit Legacy"
- Whether the email + phone number are visible

If still 404 — wait 60 seconds (Shopify CDN propagation) then refresh once. If still 404 after retry, surface back to Tristan with the page detail URL captured in Phase 3.

## Handoff

Write `docs/cowork-session-2026-05-05-contact-page.md` with:

```markdown
# Cowork Session — 2026-05-05 — Create /pages/contact

## Outcome
- [ ] Page created successfully and `/pages/contact` returns 200 with expected content
- [ ] Page created but public URL still 404s — surfacing back
- [ ] Page already existed — captured state, did not modify
- [ ] Failed at Phase ___ — surfacing back

## Phase 1
URL loaded: ___
"Add page" button visible: yes/no
Pre-existing Contact page: yes/no (if yes, captured state below)

## Phase 2
Title entered: ___
URL handle confirmed: ___
Body pasted verbatim: yes/no (if no, what differs)
Visibility: ___
Theme template: ___

## Phase 3
Save click timestamp: ___
Confirmation toast verbatim: ___
Final admin URL: ___

## Phase 4
Public URL loaded: https://8bitlegacy.com/pages/contact
HTTP status (or "page renders content"): ___
Heading visible: ___
Email visible on page: ___
Phone visible on page: ___

## Anything weird (free-form)
<verbatim screenshots of unexpected dialogs / banners / errors>
```

Commit + Syncthing-propagate. **Do NOT git push** (Tristan handles that).

## Time budget

Phase 1: 1 min
Phase 2: 3 min
Phase 3: 1 min
Phase 4: 1 min
Total: ~6 min wall clock

If exceeding 15 minutes, surface progress to Tristan rather than burning more time.
