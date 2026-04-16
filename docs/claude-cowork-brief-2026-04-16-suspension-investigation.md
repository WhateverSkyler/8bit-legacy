# Claude Cowork Brief — 2026-04-16 (Suspension Investigation)

**For:** Claude Code running on Tristan's Mac with browser access (Google Ads UI, Merchant Center, Chrome)
**From:** Claude Opus running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-16 3:45 PM EDT
**Goal:** Investigate WHY the Google Ads account (822-210-2291) is suspended and what's happening with Merchant Center (5296797260). Find the root cause and determine exactly what Tristan needs to do to fix it.

---

## Context

The Google Ads account was just suspended. The email says:

> "Your Google Ads account 822-210-2291 has been suspended for not complying with our Google Ads Terms and Conditions. Specifically, your Google Shopping Merchant account has been suspended, causing the suspension of your Google Ads account."

**BUT** when Tristan checks Merchant Center (ID: 5296797260), it shows 12K approved products and no visible suspension notice. Something doesn't add up.

The campaign `8BL-Shopping-All` (ID: 23766662629) was just created minutes before the suspension appeared. This is a brand new Google Ads account that has never spent money.

---

## Task 1 — Investigate Google Merchant Center (THOROUGHLY)

Go to https://merchants.google.com/ and check EVERYTHING:

1. **Account-level status:**
   - Look at the top banner area for any warnings, alerts, or suspension notices
   - Check if the account ID matches 5296797260

2. **Account issues page:**
   - Navigate to: Settings (gear icon) → "Account issues" or "Account-level issues"
   - OR: Look for a "Needs attention" or "Issues" section in the left sidebar
   - Screenshot/note every issue listed, even "warnings"

3. **Diagnostics page:**
   - Navigate to: Products → Diagnostics
   - Check for any account-level issues (separate from product-level issues)
   - Note any "Account suspended" or "Account warning" items

4. **Product status:**
   - How many products are approved vs disapproved vs pending?
   - Are there any products with policy violations?

5. **Free listings vs Shopping ads status:**
   - Navigate to: Growth → Manage programs (or similar)
   - Check if "Shopping ads" program shows as active, pending, or suspended
   - It's possible free listings are fine but the Shopping ads program specifically is suspended

6. **Business information:**
   - Settings → Business information
   - Is the business name, address, phone number filled in?
   - Is there a website URL verified?
   - Is identity verification complete?

7. **Linked accounts:**
   - Settings → Linked accounts
   - Is Google Ads account 822-210-2291 linked?
   - Does the link show any warnings?

**KEY INSIGHT:** Merchant Center can have products approved for "free listings" while the "Shopping ads" program is separately suspended. The 12K approved products Tristan sees might be free listings only. Check the program status specifically.

---

## Task 2 — Investigate Google Ads Suspension

Go to https://ads.google.com/ and check:

1. **Suspension banner:**
   - Click "Learn more" on the red suspension banner
   - What specific policy or reason does it cite?
   - Is there a "Request review" or "Appeal" button?

2. **Account status page:**
   - Navigate to: Tools & Settings (wrench icon) → Setup → Account status (or similar)
   - What does it say about the suspension reason?

3. **Policy Manager:**
   - Navigate to: Tools & Settings → Policy Manager
   - Are there any specific policy violations listed?
   - What policies are cited?

4. **Billing:**
   - Navigate to: Tools & Settings → Billing → Settings
   - Is there a valid payment method on file?
   - Is the billing address filled in?
   - Any billing-related warnings?

5. **Identity verification:**
   - Navigate to: Tools & Settings → Setup → Advertiser verification
   - Is there a pending identity verification?
   - Has Google requested business documentation?

6. **Campaign status:**
   - Can you still see campaign 8BL-Shopping-All (ID: 23766662629)?
   - What status does it show?

---

## Task 3 — Check for Common New-Account Suspension Causes

Based on what you find in Tasks 1-2, determine which of these applies:

### Cause A: Shopping Ads Program Not Enabled in Merchant Center
- **How to check:** Merchant Center → Growth → Manage programs → "Shopping ads"
- **Fix:** Click "Get started" or "Enable" on Shopping ads program
- **Likelihood:** HIGH — this is the most common cause

### Cause B: Business Identity Verification Required
- **How to check:** Google Ads → Tools → Advertiser verification, OR Merchant Center → Settings
- **Fix:** Submit required documentation (business license, ID, utility bill)
- **Likelihood:** MEDIUM for new accounts

### Cause C: Website Verification Incomplete
- **How to check:** Merchant Center → Settings → Business information → Website
- **Fix:** Verify and claim website URL
- **Likelihood:** LOW — was verified in earlier session

### Cause D: Missing Business Information
- **How to check:** Merchant Center → Settings → Business information
- **Fix:** Fill in business name, address, phone
- **Likelihood:** MEDIUM

### Cause E: Policy Violation on Products
- **How to check:** Merchant Center → Products → Diagnostics → Item issues
- **Fix:** Fix the specific violations
- **Likelihood:** LOW — 12K products are approved

### Cause F: Billing/Payment Issue
- **How to check:** Google Ads → Billing
- **Fix:** Add/verify payment method
- **Likelihood:** MEDIUM for accounts that have never spent

### Cause G: Automated New Account Review
- **How to check:** No specific page — if nothing else is wrong, this is it
- **Fix:** Submit appeal and wait 1-3 business days
- **Likelihood:** HIGH for first-time Shopping campaign creation

---

## Task 4 — Document Your Findings

Write a clear report of what you found. For each area checked, note:
- What you saw (exact text of any warnings/errors)
- Screenshots or exact wording of any policy violations
- What the likely root cause is
- What specific action Tristan needs to take

**Tell Tristan directly in the chat** — don't just write to a file. He needs to know:
1. What's actually wrong
2. What he needs to do to fix it
3. How long it will likely take
4. Whether the $700 promo credit and May 31 deadline are at risk

---

## Hard guardrails

- **Do NOT change any settings** — this is investigation only
- **Do NOT submit appeals** without telling Tristan first what you found
- **Do NOT modify any files** in the repo
- **Do NOT run any scripts**
- Just look, read, and report back

---

## Important URLs

- Google Merchant Center: https://merchants.google.com/
- Google Ads: https://ads.google.com/
- Google Ads Account ID: 822-210-2291
- Merchant Center ID: 5296797260
- Store URL: https://8bitlegacy.com
