# Claude Cowork Brief — 2026-04-20 (Zernio Account + API + OAuth Setup)

**For:** Claude Code running on Tristan's Mac with browser/UI automation capability
**From:** Claude Opus running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-20 08:23 AM EDT
**Goal:** Stand up a working Zernio account for 8-Bit Legacy — create account, retrieve the API key, OAuth-connect the 4 target social platforms, drop the key into `config/.env`, and verify via the smoke test.

---

## Session start — mandatory

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

If pull fails, STOP and tell Tristan.

**Read these files:**
1. `CLAUDE.md` — project rules (synced repo; pull/push at start/end)
2. `docs/podcast-automation-runbook.md` — describes how Zernio fits into the pipeline
3. `scripts/zernio_client/client.py` — the Python wrapper we'll verify with
4. `scripts/setup_zernio.py` — the smoke-test script
5. `scripts/podcast/schedule_shorts.py` + `scripts/social/schedule_photos.py` — the two consumers of the Zernio API
6. `docs/session-handoff-2026-04-19.md` — context on the podcast pipeline that's waiting on this
7. This brief

---

## Context — what Zernio is and why we need this

Zernio is a social-media scheduler used by the just-built podcast + social automation pipeline. The pipeline renders podcast shorts and product photos, then calls Zernio's REST API to schedule them multi-platform (TikTok + YouTube Shorts + IG Reels for shorts; IG + FB for photo posts).

**The pipeline is coded and dry-run green on the Linux desktop.** It's blocked on Zernio credentials only. Once this session is done, the first live run can kick off.

Key files that depend on Zernio:
- `scripts/zernio_client/client.py` — validates that `ZERNIO_API_KEY` starts with `sk_`, targets `https://zernio.com/api/v1` by default
- `scripts/setup_zernio.py` — calls `list_accounts()` + `accounts_health()`, expects 4 healthy accounts
- `scripts/podcast/schedule_shorts.py` — expects IG + FB + TikTok + YouTube OAuth'd in Zernio
- `scripts/social/schedule_photos.py` — expects IG + FB OAuth'd

**Target platforms (must all be connected and healthy at the end):**
1. **Instagram** — Professional/Business account (NOT personal)
2. **Facebook** — 8-Bit Legacy Page with admin access
3. **TikTok** — Business or Creator account
4. **YouTube** — the **8-Bit Legacy** channel (visible in Tristan's YouTube channel switcher when he's signed into Google)

---

## Before you start — ask Tristan

**Confirm these BEFORE touching anything.** Getting any one wrong cascades into broken pipeline runs.

1. **Email for the Zernio account?** Default assumption: `tristanaddi1@gmail.com`.
2. **Does he already have a Zernio account?** If yes, skip Task 1 signup and go straight to Task 2.
3. **Budget ceiling:** is he OK subscribing to Zernio's lowest paid plan that includes API access? Most schedulers gate the developer API behind paid tiers. If API access costs more than he wants to spend, we need to know before Task 4.
4. **Which accounts / handles to connect:** Tristan is already signed in to every target platform in this browser. Each OAuth flow will just show an account/page/channel picker — no typing credentials. For YouTube specifically, select the **8-Bit Legacy** channel (it appears alongside his other channels in the channel picker).
5. **IG Professional status:** is the IG account already Business or Creator? If still personal, it must be upgraded before Task 3a.
6. **FB Page link for IG:** is the IG account linked to the 8-Bit Legacy FB Page already (IG → Settings → Accounts Center → Facebook)? Required for IG Business OAuth.
7. **TikTok Business status:** is the TikTok account already Business or Creator tier? (Settings → Manage account → Switch to Business.)

**Do NOT proceed to Task 2+ without items 1, 2, and 4 confirmed.** Items 5–7 are platform-specific and can be corrected inside Task 3 if needed.

---

## Task 1 — Create (or sign into) the Zernio account (~5 min)

1. Open https://zernio.com in the browser.
2. Click **Sign up** (or **Log in** if an account already exists under Tristan's email).
3. Use the email Tristan confirmed in the pre-flight.
4. If signing up fresh:
   - Organization name: `8-Bit Legacy`
   - Accept ToS
   - Verify email if prompted (check the inbox, click the confirmation link)
5. Land on the dashboard: https://zernio.com/dashboard

**If signup requires payment to activate the API:**
- Note the cheapest plan that includes **"API access"** / **"Developer API"** as a feature
- STOP and confirm the monthly price with Tristan before entering card details
- Do NOT subscribe to a higher tier than needed

---

## Task 2 — Create a Social Set named "8-Bit Legacy" (~2 min)

Zernio groups connected accounts into Social Sets. The pipeline expects all 4 platforms to live in the same set so they share a scheduling context.

1. In the dashboard, find the Social Sets / Channels / Workspaces area (the exact label may differ — look for where connected accounts live).
2. Create a new set: `8-Bit Legacy`
3. Leave other options at defaults unless Tristan specifies otherwise.

---

## Task 3 — Connect the 4 social platforms (~20 min total)

For each platform below, in the Zernio dashboard go to the Channels / Connections area and click **Connect**. Zernio's OAuth flow opens the platform's native auth page in a new tab. Approve scopes, return to Zernio, confirm the account appears with `status=healthy`.

Tristan is already signed in to all four platforms in this browser session — the OAuth prompts will show an account/page/channel picker, not a password screen. If any platform unexpectedly asks for a password, stop and tell Tristan.

### 3a. Instagram (Business or Creator — NOT personal)

**Prereqs (check BEFORE clicking connect):**
- IG account is Professional (Business or Creator). If not: IG app → Settings → Account → Switch to Professional. Do this first.
- IG account is linked to a Facebook Page Tristan admins. If not: IG → Settings → Accounts Center → Facebook. Do this first.

**If either prereq is missing, STOP and have Tristan fix it before continuing.**

**Connect:**
1. Zernio → Connect Instagram
2. Meta prompt opens — already signed in, proceed to scope approval
3. Grant the full scope set Meta offers (profile read, content publishing, insights)
4. When the Page selector appears, pick **only** the 8-Bit Legacy-connected IG / Page
5. Return to Zernio — IG should list as healthy with the right handle

**Common failure:** Meta sometimes reverts IG to personal after scope changes. If health shows `requiresReauth` within minutes, repeat the connect flow.

### 3b. Facebook Page

1. Zernio → Connect Facebook
2. Meta prompt — already signed in, proceed
3. Meta shows a Page selector — **select only the 8-Bit Legacy Page**. Do NOT grant access to all Pages if Tristan has others.
4. Grant scopes: pages_manage_posts, pages_read_engagement, pages_show_list (or whichever Zernio requests)
5. Return to Zernio — FB should list as healthy with the right Page name

### 3c. TikTok

**Prereq:** TikTok account is Business or Creator tier. If it's personal: TikTok → Profile → Settings → Manage account → Switch to Business. Do this first.

**Connect:**
1. Zernio → Connect TikTok
2. TikTok prompt — already signed in as 8-Bit Legacy, proceed
3. Grant scopes Zernio requests (typically `video.upload`, `video.publish`, `user.info.basic`)
4. Return to Zernio — TikTok should list as healthy

**Note:** TikTok sometimes requires account verification before API publishing is enabled. If `status=requiresVerification` or similar appears, ask Tristan to verify inside TikTok's own UI first, then re-check.

### 3d. YouTube (the 8-Bit Legacy channel)

1. Zernio → Connect YouTube
2. Google OAuth prompt — already signed in, proceed
3. At the channel-selection step (Google lists the channels owned by this Google account), pick **8-Bit Legacy**
4. Grant scopes: upload videos, manage account
5. Return to Zernio — YouTube should list as healthy

**Verify:** the connected YouTube account in Zernio shows **8-Bit Legacy** as the channel name. If it shows a different channel (e.g., Tristan's personal YouTube), disconnect and redo — picking 8-Bit Legacy at the channel-selection step.

---

## Task 4 — Retrieve the API key (~3 min)

1. In the Zernio dashboard, navigate to **Settings → API Keys** (or Developers, Integrations, or similar — if the label differs, look for anywhere that mints tokens/keys).
2. Click **Create API Key** (or New Token).
3. Name: `8bit-legacy-pipeline`
4. Scope: grant the widest scope available — we need `accounts:read`, `posts:read`, `posts:write`, `media:write`. If Zernio only offers a single global scope, use it.
5. Copy the key. **It must start with `sk_`** (the client explicitly validates this prefix — a key that doesn't start with `sk_` will throw `ZernioError`).
6. Save it securely immediately — many providers show the key once only.

**If API keys are gated behind a plan Tristan hasn't activated:**
- STOP
- Report the exact plan + monthly price required
- Do NOT subscribe without explicit Tristan go-ahead

---

## Task 5 — Wire the key into `config/.env` on this Mac (~1 min)

**Important:** `config/.env` is gitignored — the key stays local to this machine. The Linux desktop will need its own copy (handoff in Task 7).

1. `config/.env` already exists per prior setup. Open it:
   ```bash
   cd ~/Projects/8bit-legacy
   open -a TextEdit config/.env   # or any editor
   ```
2. Append (or update if already present):
   ```
   # Zernio
   ZERNIO_API_KEY=sk_paste_the_key_here
   ZERNIO_BASE_URL=https://zernio.com/api/v1
   ```
3. Save. Do NOT commit `.env`. Verify it's still gitignored:
   ```bash
   git check-ignore config/.env
   ```
   Should print `config/.env`. If it doesn't, STOP — the key would get committed on the next `git add`.

---

## Task 6 — Verify with the smoke test (~3 min)

This Mac doesn't have a `.venv` yet (it was set up on the Linux desktop). Set up a minimal one just for verification:

```bash
cd ~/Projects/8bit-legacy
python3 -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv
python3 scripts/setup_zernio.py
```

**Expected output (roughly):**
```
→ Listing connected accounts…
  instagram  <id>  @<ig-handle>
  facebook   <id>  @<page-name>
  tiktok     <id>  @<tt-handle>
  youtube    <id>  8-Bit Legacy

→ Account health…
  total=4  healthy=4  expired=0  requiresReauth=0
```

**Failure modes and fixes:**
- `ZERNIO_API_KEY is not set` → `.env` not loaded. Check path, check for stray whitespace, ensure the line is `KEY=value` with no surrounding quotes.
- `Auth failed (401)` → key was mis-copied; regenerate it and retry.
- `API key looks wrong — Zernio keys start with 'sk_'` → you pasted a client ID or secret instead of the key.
- A platform is missing from the list → that OAuth didn't complete; redo Task 3 for that platform.
- Any account `status != healthy` → reauth that platform from the Zernio dashboard.

**Do NOT run `--smoke-post`** — that attempts a live post. The default `list + health` verification is all this session needs.

---

## Task 7 — Handoff to Linux desktop (Tristan action, not yours)

The actual podcast + social pipeline runs on the Linux desktop. It needs the same key locally.

**Tell Tristan in chat (paste something like this):**
```
Zernio is live. To sync to your Linux desktop:

  cd ~/Projects/8bit-legacy && git pull --ff-only
  # Open config/.env (gitignored, NOT pulled from git) and add:
  ZERNIO_API_KEY=sk_<same key>
  ZERNIO_BASE_URL=https://zernio.com/api/v1
  source .venv/bin/activate
  python3 scripts/setup_zernio.py   # expect total=4 healthy=4
```

**Do NOT post the actual key in chat, in a doc, in git, in Slack, etc.** Hand it to Tristan via a secure channel (his password manager, an encrypted note). The workflow assumption is: Tristan copies the key manually from the Zernio dashboard when he's at the Linux machine.

---

## Hard guardrails

- **Never commit `config/.env`** — it's gitignored for a reason. Run `git status` before any commit and confirm `.env` is not staged.
- **Never post the API key** anywhere except the local `config/.env` file and Tristan's password manager.
- **Do NOT schedule any test posts.** Smoke test uses GET endpoints only.
- **Do NOT subscribe to a paid plan** without explicit Tristan approval on the price.
- **Do NOT grant access to all FB Pages** if Tristan has multiple — select only the 8-Bit Legacy Page.
- **Do NOT connect IG if it's still personal** — upgrade to Professional first.
- **Do NOT pick the wrong YouTube channel** during OAuth. Verify the selected channel is **8-Bit Legacy** before granting access — NOT Tristan's personal YouTube.
- **Do NOT touch existing `.env` vars** — only add Zernio-specific keys. Other credentials (Shopify, Google Ads, eBay) are already in use by the dashboard and scheduler.
- **Do NOT run any Python scripts** other than `setup_zernio.py`.
- **Do NOT modify files in `dashboard/`, `scripts/` (other than reading them), or `config/` (other than appending to `.env`)**.

---

## When you're done

1. Commit only the handoff doc (no secrets):
   ```bash
   git add docs/cowork-session-2026-04-20-zernio.md
   git status   # verify no .env or secrets staged
   git commit -m "Cowork 2026-04-20: Zernio account + API + OAuth setup"
   git push
   ```
2. Write a handoff note at `docs/cowork-session-2026-04-20-zernio.md` containing:
   - GREEN / BLOCKED / SKIPPED per task
   - Which platforms ended up connected (with handles)
   - Any plan / payment decisions made (and price paid, if any)
   - The exact message for Tristan to mirror the key on Linux (WITHOUT the key itself)
   - Any OAuth quirks encountered (for future reference)
3. Tell Tristan in chat whether the smoke test printed `total=4 healthy=4` and what's needed from him on the Linux side.

---

## Success criteria

- [ ] Zernio account active on confirmed email
- [ ] Social Set `8-Bit Legacy` exists
- [ ] Instagram (Business/Creator) connected, `status=healthy`
- [ ] Facebook Page (8-Bit Legacy) connected, `status=healthy`
- [ ] TikTok (Business/Creator) connected, `status=healthy`
- [ ] YouTube (8-Bit Legacy channel) connected, `status=healthy`
- [ ] API key created, starts with `sk_`, named `8bit-legacy-pipeline`
- [ ] `ZERNIO_API_KEY` + `ZERNIO_BASE_URL` present in `config/.env` on Mac
- [ ] `config/.env` still gitignored; nothing secret committed
- [ ] `python3 scripts/setup_zernio.py` prints `total=4 healthy=4`
- [ ] Handoff note pushed; instructions transmitted to Tristan to mirror on Linux
