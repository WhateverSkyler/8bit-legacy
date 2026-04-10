# VPS Dashboard Status — 2026-04-10

**Auditor:** Claude (cowork / browser session)
**Tied to brief:** `docs/claude-cowork-brief-mac-2026-04-10-pm.md` Task E
**Scope:** Confirm whether `https://8bit.tristanaddi.com` is reachable, what is blocking it, and document the env var / credential situation.

---

## TL;DR

`https://8bit.tristanaddi.com` is **not reachable** without credentials. The browser loads an error page when navigating to it, which matches what the terminal session reported earlier today (`nginx 401 Authorization Required`). This means nginx has HTTP basic auth enabled in front of the Next.js dashboard and no credentials were supplied.

**Blocked: need Tristan to provide credentials or disable basic auth.**

---

## What I observed

- Navigated to `https://8bit.tristanaddi.com` in a fresh browser tab.
- Chrome's frame immediately entered an "error page" state — the browser automation tools returned `Frame with ID 0 is showing error page` for both the screenshot and the `get_page_text` calls.
- `document.body.innerText` returned empty — there is no HTML content rendered, which is the standard outcome when a basic-auth prompt is dismissed without credentials.
- No JavaScript executed on the page. Which means it is NOT the dashboard's own login page (Next.js would render at least the login HTML). It is the nginx layer rejecting the request before the app is reached.

The behavior is consistent with the terminal session's earlier finding of `nginx 401 (no basic-auth creds in .env)`.

---

## What I could not verify

Because I cannot get past the basic-auth prompt, I cannot confirm any of the things the brief asked me to check inside the dashboard:

- [ ] Dashboard loads
- [ ] `/scheduler` page shows the 5 jobs healthy (last run + next run)
- [ ] No tripped circuit breakers
- [ ] Env var name for the basic-auth credentials

---

## Possible fixes (pick one)

1. **Provide basic auth credentials to the terminal session.** If Tristan stores them in 1Password / Keychain / a password manager, the terminal Claude can add them to `config/.env` under something like `VPS_DASHBOARD_AUTH_USER` / `VPS_DASHBOARD_AUTH_PASS`. **Never commit these.**

2. **Remove the nginx basic auth and use the dashboard's own auth layer.** The Next.js dashboard can implement its own login with Shopify OAuth, NextAuth, or a signed-cookie session. Simpler long-term because the terminal session (and future Claude sessions) can then hit the API without basic-auth gymnastics.

3. **Keep basic auth but allowlist the Mac IP.** If the dashboard is only ever accessed from Tristan's Mac, allowlisting can remove the auth friction without losing protection from the public internet.

My recommendation is **option 2** — a single auth layer is less error-prone than two.

---

## Blocker for other tasks

- The terminal Claude session mentioned it can't reach scheduler status without credentials. This blocks automated health-checking of the 5 scheduled jobs (`shopify-product-sync`, `google-ads-sync`, `fulfillment-check`, `price-sync`, `pokemon-price-sync`).
- Recommend unblocking this before the Google Ads launch so the fulfillment/price/ads automation can be observed reliably.

---

## What I did NOT do

- Did not attempt to brute-force or bypass the nginx basic auth (explicitly prohibited by guardrails)
- Did not write any credential to any file
- Did not fetch via `curl`, `wget`, or Python (also prohibited by WebFetch restrictions)
