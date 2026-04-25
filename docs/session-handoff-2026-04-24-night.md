# Session handoff — 2026-04-24 night (Linux desktop)

**Closed at:** Fri 2026-04-24 ~22:02 ET

## What this session was supposed to do

Per `docs/claude-desktop-brief-2026-04-24-vps-dashboard.md`: SSH into the
VPS and stop the 8-Bit Legacy dashboard's internal scheduler so it stops
running stale safety thresholds against live ads.

## What actually happened

**Did not deprecate the VPS scheduler.** Re-routed the session into
*finding* the VPS first, because the user couldn't locate the box in
master-hand. Now we know:

- Personal VPS is **Hetzner Cloud**, `178.156.201.13`, Ubuntu 24.04,
  **CloudPanel** (not Plesk).
- 8-Bit Legacy dashboard runs as the `bitlegacy` site-user on that box:
  PM2 → `next start --port 3002`, repo at `/home/bitlegacy/htdocs/`,
  fronted by nginx + Varnish, gated by basic auth.
- No Docker on this VPS — different model than TrueNAS.
- SSH alias `hetzner` was pointing at the wrong key (`id_ed25519`) and
  getting denied. Fixed to `id_ed25519_linux` in `~/.ssh/config`.
  `ssh hetzner` now connects clean.

## Knowledge persisted (so we don't redo this)

- **`~/Projects/Claude Workspace 2.0/docs/INFRASTRUCTURE.md`** — new doc,
  cross-machine, the canonical "what server runs what" reference.
  Master-hand README now links it.
- Memory files updated:
  - `~/.claude/projects/-home-tristan/memory/personal-plesk.md` — fixed
    SSH key path, added the 3 sites it was missing (8bit, jamtracker,
    photos), pointed at the new INFRASTRUCTURE.md.
  - `MEMORY.md` index updated to match.

## What still needs doing (next session, Mac or Linux)

The VPS scheduler deprecation is **still open**. The brief at
`docs/claude-desktop-brief-2026-04-24-vps-dashboard.md` is still the
right runbook — only difference is now SSH access is a known-good
one-liner:

```bash
ssh hetzner   # working alias on Linux desktop after tonight's fix
```

Once on the box:
- Dashboard is at `/home/bitlegacy/htdocs/` running under bitlegacy's
  PM2 daemon (PID 256649).
- `sudo -u bitlegacy pm2 list` from root will show the process. Stop
  with `sudo -u bitlegacy pm2 stop <id>` (Option B from the brief), or
  add `DISABLE_SCHEDULER=1` to its `.env.local` and restart (Option A,
  only if the env-guard is in `scheduler.ts` — grep first).
- Don't delete the PM2 entry; user wants the UI revivable later.

The TrueNAS ads safety cron continues to auto-recover from any
false-trips in the meantime, so this is not on fire — just an ugly
2-hour recovery window that we want to close before ads launch.

## Other open state at EOD

- `deploy/deploy-to-truenas.sh` has uncommitted edits and `podcast-assets/`
  is untracked. Both pre-date this session — leaving them alone.
- Pixel-fix verification from earlier today still pending (per the prior
  EOD doc `session-handoff-2026-04-24.md`).
