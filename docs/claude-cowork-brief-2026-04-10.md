# Claude Cowork Brief — 2026-04-10

**For:** Claude running on Tristan's MacBook with browser/UI automation capability
**From:** Claude Opus 4.6 on Linux desktop (same repo, 8bit-legacy)
**Context:** Tristan is splitting work between machines today. Desktop Claude is handling CLI/script/docs tasks. You are handling the browser + Shopify admin + theme editor work that requires UI interaction.

---

## Session start — read these first

Before doing anything, pull these into context:

1. `CLAUDE.md` — full project instructions
2. `docs/google-ads-launch-plan.md` — freshly drafted today, describes the ads launch. You don't need to execute anything in here, but it gives you context on why the website work matters.
3. `docs/sale-wave-plan-april-2026.md` — the sale strategy Tristan will approve; your homepage work needs to support it.
4. `docs/sale-banner-concepts.md` — banner concepts; Concept 1 is recommended. Tristan designs the banner in Affinity — you just need to know what's coming so the homepage layout accommodates it.
5. `~/.claude/projects/-home-tristan-Projects-8bit-legacy/memory/project-website-todos.md` — authoritative task list.

Then pull the repo:
```bash
cd ~/Projects/8bit-legacy   # or wherever it lives on Mac
git pull --ff-only
```

(Per CLAUDE.md, 8bit-legacy is synced via GitHub between Linux desktop and Mac. Always pull at session start.)

---

## Your three tasks

### Task 1 — Verify the 10% off popup email destination (PRIORITY: HIGH, ~20 min)

**The problem:** Tristan noticed the homepage has a 10% off email-signup popup but has never verified where collected emails actually go. Possible revenue leak if the popup is broken or disconnected.

**What to do:**
1. Log in to the Shopify admin for 8bitlegacy.com (Tristan's machine should already be logged in via a browser session — if not, ask him to log in manually)
2. Go to **Online Store → Themes → Customize** and find the popup block. Identify which app is powering it (could be Shopify-native, Klaviyo, Mailchimp, Privy, etc.)
3. Open the connected email app and verify:
   - [ ] Is the app actually connected (OAuth valid)?
   - [ ] How many emails have been collected in the last 30 days?
   - [ ] Are those emails going into a usable list/segment?
   - [ ] Is there an automated welcome flow sending the 10% off code?
   - [ ] Is that welcome flow actually firing (check send stats)?
4. If the popup is broken or emails are going nowhere, document the specific failure and propose a fix.
5. If it's working, confirm how many subscribers total, and whether there's an active email marketing flow.

**Deliverable:** A short status note in `docs/email-popup-audit-2026-04-10.md`. Include: which app powers the popup, subscriber count, welcome flow status, and any action items for Tristan.

**DO NOT:**
- Change any email app settings without asking Tristan first
- Send any test emails from the real list
- Delete or modify any subscriber data

---

### Task 2 — Homepage redesign below "Deals of the Week" (PRIORITY: MEDIUM, ~45 min)

**The problem:** Tristan said everything below the "Deals of the Week" section on the homepage looks "half-assed." Needs visual polish.

**Context to load first:**
- Open https://8bitlegacy.com in a browser and scroll through the full homepage
- Take a screenshot of the "Deals of the Week" section and everything below it
- Identify each section and what feels off (likely: inconsistent spacing, mismatched fonts, weak imagery, broken layouts, duplicate content, or placeholder/stock content that was never replaced)

**Brand anchors (these must be honored):**
- Orange `#ff9526`, sky-blue `#0EA5E9`
- Nunito font family
- Light theme only (no dark sections unless intentional accent)
- Nintendo Switch-inspired clean aesthetic — not cluttered retro-kitsch

**What to do:**
1. In the Shopify theme editor (Online Store → Themes → Customize), review each section below "Deals of the Week"
2. Identify the 3-5 specific issues making it feel half-finished
3. Propose fixes — don't apply them yet. Write them up in `docs/homepage-redesign-notes.md` with screenshots and specific actions (e.g., "Section 4: swap placeholder image for Pokemon collection hero, change heading font from Arial to Nunito Bold, add 40px bottom padding")
4. Rank fixes by impact/effort
5. Ask Tristan which to apply first

**If Tristan gives explicit approval in the session:** apply the approved fixes in the theme editor. Always save a theme backup first (Shopify → Themes → duplicate current theme before editing).

**DO NOT:**
- Make unapproved changes to the live theme
- Delete or reorder sections without explicit approval
- Change brand colors or fonts
- Touch sections ABOVE "Deals of the Week" (those are working fine)

---

### Task 3 — Recheck the Shop sales channel (PRIORITY: LOW, ~5 min)

**The problem:** Per `docs/ecommerce-infrastructure-audit-2026-04-06.md` (Task 5), the Shop sales channel was showing "Action needed" due to the CIB variants being out of stock. The CIB variants have since been fixed (see CLAUDE.md completed list: "All CIB variants purchasable (6,112 fixed)").

**What to do:**
1. Shopify admin → Sales channels → Shop
2. Check if the "Action needed" badge is still there
3. If it's gone, mark this as complete in the audit doc
4. If it's still there, identify the new reason and document it

**Deliverable:** Update `docs/ecommerce-infrastructure-audit-2026-04-06.md` Task 5 with the current status, or create a quick `docs/shop-channel-status-2026-04-10.md` note.

---

## What I (desktop Claude) already handled today

So you don't duplicate my work:

- ✅ Checked Pokemon set availability (`me3` and `me2pt5`) — confirmed both blocked waiting on TCGPlayer pricing in the Pokemon TCG API. Do not attempt an import.
- ✅ Ran profit report — 5 orders in 6 months, $508 revenue, 22.7% margin. Store is cold. This info is in the Google Ads plan and sale plan docs.
- ✅ Wrote `docs/google-ads-launch-plan.md` — the full launch playbook
- ✅ Wrote `docs/sale-wave-plan-april-2026.md` — 4-layer sale strategy
- ✅ Wrote `docs/sale-banner-concepts.md` — 5 banner concepts for Tristan to choose from
- ✅ Updated `project-website-todos.md` memory — marked collection sorting done
- ✅ Updated this brief

You don't need to touch any of the above.

---

## When you're done

1. Commit your changes to the repo:
   ```bash
   git add docs/
   git commit -m "Add email popup audit + homepage redesign notes (cowork session)"
   git push
   ```
2. Leave a brief summary in `docs/cowork-session-summary-2026-04-10.md` with:
   - What you did
   - What's blocked and needs Tristan
   - Anything unexpected you found
3. If Tristan is still in the session, tell him what to review.

---

## Guardrails

- **Never commit secrets.** `.env` files are gitignored but be careful if you see tokens in screenshots or logs.
- **Don't run `manage-sales.py --apply` or any destructive script.** That's for desktop Claude with Tristan's direct approval.
- **Don't touch Google Ads.** The conversion tracking and launch are on Tristan's manual to-do list.
- **Pull at the start, push at the end.** 8bit-legacy is a synced repo.
- **Any UI task that modifies the live store:** ask first, apply second.

---

## Questions to ask Tristan if unclear

- Do you want me to apply the homepage fixes I identify, or just document them for your review?
- Is the email popup supposed to be Klaviyo, or something else? (helps me identify what's there)
- Any specific sections below "Deals of the Week" you want me to prioritize or skip?

Good luck. Ping me (desktop Claude) via Tristan if you hit anything blocking.
