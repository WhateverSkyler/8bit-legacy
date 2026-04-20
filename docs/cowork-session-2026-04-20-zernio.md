# Cowork Session — 2026-04-20 (Zernio Setup)

**Operator:** Claude (Cowork mode, on Tristan's Mac)
**Brief:** `docs/claude-cowork-brief-2026-04-20-zernio-setup.md`
**Status:** All in-browser tasks done. One verification step blocked by sandbox network policy and must be re-run on Tristan's Mac.

---

## Outcome

| Task | Status |
|---|---|
| 1. Verify Zernio login (Accelerate plan, tristanaddi1@gmail.com) | done |
| 2. Create Profile "8-Bit Legacy" | done — id `69e6242624fae2a451735635` |
| 3. OAuth-connect IG / FB / TikTok / YouTube | done — 4/4 connected |
| 4. Create API key starting with `sk_` | done — name `8bit-legacy-pipeline`, scope `8-Bit Legacy` only, Read & Write |
| 5. Write `ZERNIO_API_KEY` + `ZERNIO_BASE_URL` into `config/.env` | done — verified `git check-ignore` → ignored |
| 6. Smoke test `python3 scripts/setup_zernio.py` | **blocked by sandbox** — see below |
| 7. Handoff note + commit | this file |

---

## Connected accounts (verified visually in Zernio dashboard)

All four platforms show `connected` on https://zernio.com/dashboard/connections under the **8-Bit Legacy** profile:

| Platform | Handle | Notes |
|---|---|---|
| Facebook | @8bitlegacyco | Page id `110126491984809` (Video Game Store). Full Pages scopes granted (post, comments, insights, metadata, messaging). |
| Instagram | @8bitlegacyretro | IG Business account, linked through Meta Business. |
| TikTok | @8bitlegacy.com | All 6 TikTok scopes granted (basic profile, additional profile, stats, public videos, post content, upload draft). |
| YouTube | @8bitlegacyretro | Brand channel under sideshowtristan@gmail.com (Tristan confirmed ownership). All 4 YT scopes granted. |

---

## API key

- Name: `8bit-legacy-pipeline`
- Profile scope: 8-Bit Legacy only (toggled off "Full access (all profiles)")
- Permission: Read & Write
- Prefix: `sk_8cba3...` — starts with `sk_` ✓
- Stored in: `config/.env` (gitignored)
- The full key is **only viewable once**. It has been written to `config/.env`. There is no copy in this repo, in this doc, or in any commit.

The pre-existing `Default Key` (`sk_b1779...16e2d47e`) was left alone.

---

## What's blocked and why

`scripts/setup_zernio.py` could not run inside the Cowork sandbox because the sandbox's outbound proxy (`localhost:3128` + SOCKS5 fallback) does not allow `zernio.com`. Both `requests` and `curl` get a 403 from the proxy on CONNECT.

This is a sandbox limitation, not a Zernio problem. **Tristan needs to run the smoke test on the Mac itself:**

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
python3 -m venv .venv  # if not already there
.venv/bin/pip install requests python-dotenv
.venv/bin/python3 scripts/setup_zernio.py
```

Expected output (matching the brief's success criteria):

```
→ Listing connected accounts…
  facebook   <id>   @8bitlegacyco
  instagram  <id>   @8bitlegacyretro
  tiktok     <id>   @8bitlegacy.com
  youtube    <id>   @8bitlegacyretro

→ Account health…
  total=4  healthy=4  expired=0  requiresReauth=0
```

If the health line shows anything other than `healthy=4`, click into the warning row in the Zernio dashboard and re-run the relevant OAuth.

---

## Linux-mirror instructions (no key in transit)

The repo on the Linux box also needs `ZERNIO_API_KEY` to run the schedulers. Do **not** copy `config/.env` over the wire and do **not** paste the key into chat. Re-fetch it instead:

1. On the Linux box: `cd ~/Projects/8bit-legacy && git pull --ff-only` (this brings down the schedulers + this doc but **not** the key).
2. From any browser on the Linux box: log into https://zernio.com → Settings → API Keys → use the existing `8bit-legacy-pipeline` key. (If you didn't store it the first time, create a new one — the old one is invalidated automatically on first use of the new one only if you delete it, so feel free to rotate.)
3. Append to `config/.env`:
   ```
   ZERNIO_API_KEY=sk_...
   ZERNIO_BASE_URL=https://zernio.com/api/v1
   ```
4. Run the same smoke test as above.

---

## Files changed in this commit

- `config/.env` — gitignored, **not** in commit
- `docs/cowork-session-2026-04-20-zernio.md` — this file
- `docs/claude-cowork-brief-2026-04-20-zernio-setup.md` — the brief itself was untracked; included in same commit

No code changes. The OAuth + API-key creation is all in Zernio's hosted dashboard.

The commit landed on `main` locally. **The Cowork sandbox can't push** (no GitHub creds). Tristan needs to:

```bash
cd ~/Projects/8bit-legacy && git push origin main
```

That'll publish the 7 commits ahead of `origin/main` (6 prior + this one).

---

## What unblocks next

With Zernio wired, both consumers in the pipeline are ready to run:

- `scripts/podcast/schedule_shorts.py --episode "Episode April 14th 2026" --start-date 2026-04-21 --dry-run`
  → schedules vertical shorts to TikTok + YouTube + Instagram (3/day at 9/13/19 ET).
- `scripts/social/schedule_photos.py --start-date 2026-04-21 --preview`
  → schedules product photos from `data/social-media/final/*.png` to IG + FB (2/day at 10/18 ET).

Run each in `--dry-run` / `--preview` first; flip to `--execute` once Tristan eyeballs the captions.

---

## Pre-flight answers (recorded for the next operator)

- Zernio account: existing, `tristanaddi1@gmail.com`, on Accelerate (paid).
- Browser: all four platforms already logged in.
- TikTok account: already a Business/Creator tier (no `requiresVerification`).
- YouTube channel ownership: brand channel owned by `sideshowtristan@gmail.com`, with `tristanaddi1@gmail.com` as an authorized user.
- Meta account: had to switch mid-flow to the correct one (Tristan fixed in browser); 8-Bit Legacy Page id `110126491984809` is the canonical FB Page.

---

## Hard guardrails respected

- No paid-plan upsells triggered (already on Accelerate).
- No code/account/repo destructive actions.
- `config/.env` never committed (`git check-ignore` confirmed before write).
- API key visible only once → captured straight into `.env`, not echoed elsewhere.
- Smoke-post (`--smoke-post`) flag intentionally **not** used; brief said pipeline-driven posts only.
