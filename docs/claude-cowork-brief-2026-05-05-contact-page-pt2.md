# Cowork Brief — 2026-05-05 PART 2 — Edit Existing Hidden Contact Page

## Goal

The previous brief discovered the Contact page already exists in Shopify Admin (ID `145471406114`) but is set to **Hidden**, which is why `/pages/contact` returns 404 publicly. Shopify serves Hidden pages as 404 to non-admin visitors.

This brief tells you to edit it in place: flip Visibility → Visible, paste body content, keep the existing custom theme template (it may already render a contact form for free).

Time budget: ~4 minutes.

## Hard guardrails — read first

✗ Do NOT delete the existing page (it has handle = `contact` already, which we want)
✗ Do NOT change the page handle (it's already `contact` — leave it)
✗ Do NOT change the theme template selection (it's currently `contact` template — KEEP IT)
✗ Do NOT modify any other page, theme code, app, or setting
✗ Do NOT preview or modify the `templates/page.contact.liquid` theme file directly — leave the theme alone
✗ Do NOT change SEO title/description/handle from defaults
✗ Do NOT enable comments
✗ Do NOT change "Online store" channel availability if currently checked

If the page is no longer Hidden when you arrive (e.g. someone else flipped it manually), STOP and surface back. Don't paste body content over what's there.

## Phase 1 — Open the existing page (1 min)

URL: `https://admin.shopify.com/store/dpxzef-st/pages/145471406114`

Capture verbatim:
- Page title field (should currently be "Contact" or similar — capture exactly)
- Visibility dropdown current value (expected: "Hidden")
- Theme template current selection (expected: `contact` — capture exactly)
- Body editor — confirm it's empty or has only whitespace
- URL handle field — confirm it shows `contact`

If the title is empty or differs from "Contact", set it to:
```
Contact
```

## Phase 2 — Edit the page (2 min)

### 2a. Set body content

Click into the body editor. Paste this content (use the rich-text editor's paste-from-markdown if available, else type/paste the equivalent with the toolbar buttons):

```
We're here to help with any questions about your retro games, Pokemon cards, or order.

Email: support@8bitlegacy.com
Phone: (229) 329-2327
Hours: Monday – Friday, 9 AM – 5 PM Eastern Time

For order-related questions, please include your order number in your message and we'll get back to you within one business day.

Returns and warranty information is available on our Shipping, Returns & Warranty Policy page.
```

If your theme's contact template already renders a contact form automatically (most do), this body content will appear ABOVE or alongside the form. That's fine.

If the rich-text editor strips line breaks or formatting, just paste as plain text — readability is the goal, not styling.

### 2b. Flip visibility

Find the Visibility control (right sidebar in modern Shopify, or below body content in older versions). Change from **Hidden** to **Visible**.

If there's a "Set visibility" date/time picker, leave it on the immediate/now option (do NOT schedule for a future date).

### 2c. Verify what you should NOT have changed

Before saving, double-check:
- Theme template is still `contact` (NOT changed to `page`)
- URL handle is still `contact`
- Page title is "Contact"
- No SEO/social metadata fields touched

## Phase 3 — Save (30 sec)

Click **Save** (top right or wherever the Save button is in your Shopify version).

Wait for confirmation toast (typically "Page saved" / "Page updated").

Capture:
- Save click timestamp
- Confirmation toast verbatim
- Re-confirm Visibility dropdown now reads "Visible" after the save

## Phase 4 — Verify public URL works (1 min)

Open a new tab (incognito if convenient — but not required) and load:
```
https://8bitlegacy.com/pages/contact
```

Capture:
- HTTP response (page loads with content vs 404)
- Whether the body content you pasted is visible
- Whether a contact FORM is rendered on the page (text fields for Name / Email / Message and a Submit button) — this tells us whether the custom contact template was set up to render a form
- The page heading (likely "Contact" pulled from the title)

If still 404 — wait 60 seconds for Shopify CDN propagation, then refresh once. If still 404 after retry, surface back to Tristan with screenshots.

If you see a JavaScript / theme error rendered (rare but possible if the custom template references missing snippets), capture the error message verbatim and surface back.

## Handoff

Append to `docs/cowork-session-2026-05-05-contact-page.md` (the file the previous session started):

```markdown

---

## Part 2 — Edit existing page (2026-05-05 — second session)

## Outcome
- [ ] Page now Visible at /pages/contact, body content visible, page renders without errors
- [ ] Page Visible but body content didn't render correctly — surfacing back
- [ ] Public URL still 404s after save + retry — surfacing back
- [ ] Theme template error rendered on public page — surfacing back

## Phase 1 — Page state at open
URL loaded: ___
Title field: ___
Visibility before edit: ___
Theme template selected: ___
Body before edit: empty / not empty (describe)
URL handle: ___

## Phase 2 — Edits
2a. Body content pasted: yes/no (note any formatting issues)
2b. Visibility changed Hidden → Visible: yes/no
2c. Confirmed unchanged: theme template, handle, title, SEO fields

## Phase 3 — Save
Save click timestamp: ___
Confirmation toast verbatim: ___
Visibility after refresh: ___

## Phase 4 — Public verification
URL: https://8bitlegacy.com/pages/contact
HTTP status (or "renders content"): ___
Body content visible: ___
Contact FORM rendered: yes/no (this tells us if the custom template gave us a form for free)
Page heading visible: ___
Any errors visible on the page: ___

## Anything weird (free-form)
<verbatim screenshots of unexpected dialogs / banners / errors>
```

Commit + Syncthing-propagate. **Do NOT git push** (Tristan handles that).

## Time budget

Phase 1: 1 min
Phase 2: 2 min
Phase 3: 30 sec
Phase 4: 1 min
Total: ~4 min wall clock

If exceeding 10 minutes, surface progress to Tristan rather than burning more time.
