# Claude Desktop Brief — 2026-04-24 — VPS Dashboard Deprecation

## The task in one sentence

Stop the VPS dashboard (`8bit.tristanaddi.com`) from running the scheduled automation jobs, keep its UI up as a visual-only endpoint for later, and hand off ALL operational duties to TrueNAS (already set up this afternoon).

## Why now

- TrueNAS is already running the ads safety check + daily report + budget-revert crons as of 2026-04-24. See `docs/session-handoff-2026-04-24.md` for list.
- The VPS still runs its own `google-ads-sync` + `fulfillment-check` + `price-sync` + `pokemon-price-sync` + `shopify-product-sync` jobs at old thresholds (e.g. `$25 MAX_DAILY_AD_SPEND` in `dashboard/src/lib/safety.ts`). When the ads campaign launches, the VPS will false-trip on the stale $25 cap and attempt to pause the campaign via the Ads API.
- My TrueNAS safety cron (id 660) auto-recovers from those false-trips within 2h, but that's ugly. Better to just stop the VPS from running its scheduler at all.
- Per user direction today: "everything operational/functional should be setup on my TrueNAS Server … that VPS Dashboard will just solely be a visual dashboard i can visit later down the road once we stabilize."

## Hard guardrails

- **DO NOT delete the VPS dashboard app or its code.** User wants to return to it later as a visual dashboard.
- **DO NOT touch the TrueNAS `8bit-pipeline` container** — it's doing the real work now.
- **DO NOT touch the paused Google Ads campaign.** Main Mac session handles the flip autonomously; you just kill the scheduler.
- If SSH to the VPS doesn't work, stop and document why — don't improvise.

## Context you need

- **VPS URL:** `https://8bit.tristanaddi.com` (nginx basic-auth 401 — no creds in repo)
- **Repo on VPS:** somewhere that serves `dashboard/` — SSH in to find the process manager (likely pm2, systemd, or docker-compose). Reference: `docs/vps-dashboard-status-2026-04-10.md` + `memory/project_vps_dashboard.md`
- **VPS host:** `tristanaddi.com` (subdomain), underlying host should be in Plesk. SSH key on the machine is likely `~/.ssh/plesk_criticalmkt` or another Plesk key. **Mac session tried and got the wrong server, so you'll need to figure out which SSH alias reaches it from the Linux desktop.**

## Step 1 — SSH in and identify the process manager (5 min)

Try the likely SSH paths:

```bash
# most likely:
ssh 8bit.tristanaddi.com
# or via plesk key:
ssh -i ~/.ssh/plesk_criticalmkt <username>@8bit.tristanaddi.com
# or whatever the Linux desktop has configured that worked last time
```

Once in, find the running dashboard:

```bash
# process manager options — check each:
pm2 list                        # Node-first
systemctl list-units --type=service --state=running | grep -i 8bit
docker ps | grep -i 8bit        # if it's containerized
```

Also find the repo root:

```bash
ls ~/8bit-legacy || ls /var/www/8bit-legacy || find / -name "safety.ts" -path "*dashboard*" 2>/dev/null | head -3
```

**Report what you find** in `docs/cowork-session-2026-04-24-vps.md` (or similar) for the Mac session to use next time.

## Step 2 — Stop the scheduler, keep the UI alive (5 min)

Goal: `dashboard/src/lib/scheduler.ts` stops running its 5 jobs, but the Next.js server keeps serving pages.

The scheduler is kicked off somewhere on app startup (search for `startScheduler` or `node-cron` imports). Cleanest options:

### Option A — Kill the scheduler via env var

Add `DISABLE_SCHEDULER=1` to the VPS's `dashboard/.env.local`, then restart the process. The main session on Mac will add an `if (process.env.DISABLE_SCHEDULER) return` guard into the scheduler entry point in a follow-up commit. **If the env-var guard doesn't already exist in the code, Option A won't work without a code change — skip to Option B.**

Actually let me check: this requires the guard to exist in `dashboard/src/lib/scheduler.ts`. Grep for `DISABLE_SCHEDULER`:

```bash
grep -rn "DISABLE_SCHEDULER" ~/Projects/8bit-legacy/dashboard/src/
```

- If present → set env var, restart dashboard
- If absent → use Option B

### Option B — Stop the whole dashboard process

Simpler, removes both scheduler and UI (user accepts — UI was visual-only anyway, no one depends on it):

```bash
pm2 stop <dashboard-process-name>
# or
sudo systemctl stop 8bit-dashboard
# or
cd <repo-root> && docker compose stop dashboard
```

Leave the process-manager entry in place (so user can `pm2 start` to revive the UI later when they want to visit).

### Option C — Half-and-half via systemd override

If scheduler is a separate service from the web UI (e.g., one pm2 app runs the Next.js server, another runs the cron worker) — stop just the scheduler one.

Pick whichever matches the actual setup on the VPS. Lean toward Option B unless Option A is trivially available.

## Step 3 — Verify

1. Run `pm2 list` (or equivalent) — scheduler stopped or whole dashboard stopped.
2. From Mac/Linux: `curl -I https://8bit.tristanaddi.com` — expect `401` still (nginx basic auth) or `502`/`connection refused` if the whole server went down. Both are fine per scope.
3. Wait 10 minutes, then check the TrueNAS ads safety cron last run — should still be firing cleanly from TrueNAS side:
   ```bash
   ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 'tail -5 /mnt/pool/apps/8bit-pipeline/data/ads_safety.log'
   ```
4. In the Google Ads UI (or via the API), verify the campaign status hasn't mysteriously flipped back to PAUSED from a VPS action. (Mac may have already flipped it ENABLED autonomously — that's fine, we want ENABLED.)

## Step 4 — Handoff note

Write `docs/cowork-session-2026-04-24-vps.md` with:
- Which SSH path reached the VPS
- Which process manager was running the dashboard (pm2 / systemd / docker)
- Which option (A/B/C) was applied
- Commands used
- Any surprises

Commit + let Syncthing propagate:

```bash
cd ~/Projects/8bit-legacy
git add docs/cowork-session-2026-04-24-vps.md
git commit -m "desktop: VPS dashboard scheduler deprecated; UI stays up for later"
git push  # Linux desktop should have working GitHub creds. If not, Syncthing still carries it to Mac.
```

## Success criteria

- [ ] SSH reached the VPS from Linux desktop
- [ ] Process manager identified + documented
- [ ] Scheduler stopped (Option A, B, or C applied)
- [ ] TrueNAS ads safety cron still firing cleanly
- [ ] Handoff doc committed
- [ ] Dashboard UI either deliberately stopped (Option B) or still up (Option A/C) — user accepts either

## What you are NOT doing

- Not migrating the dashboard's code or data anywhere. That happens much later.
- Not rewriting `dashboard/src/lib/safety.ts`. TrueNAS is authoritative now.
- Not reconfiguring nginx. Basic auth stays.
- Not touching the ads campaign.
