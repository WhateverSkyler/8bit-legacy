# Session Handoff — 2026-04-24 EOD

**Resume target:** later tonight (on Linux desktop) or tomorrow.
**Previous:** `docs/session-handoff-2026-04-23.md`

---

## TL;DR

1. **Podcast short-form pipeline got a permanent fix** — per-scene crop detection replaces yesterday's single-offset face detect. 8 Ep14 clips re-rendered + re-scheduled across 4 platforms (TikTok, YouTube, Instagram, **Facebook** — Facebook was missing from `TARGET_PLATFORMS` until today).
2. **Ads infrastructure built out end-to-end.** CIB exclusion (6,112 variants), TrueNAS-resident safety + daily report + budget-revert cronjobs, $22/day budget set. Campaign still **PAUSED** — waiting on one final verification gate.
3. **Purchase pixel was broken and is now (probably) fixed.** Cowork uninstalled + reinstalled the Google & YouTube Shopify app and ran the "Migrate Google tags" wizard — competing tag injectors (MonsterInsights GA4 + Shopify Channel App MC) had been clobbering G&Y's pixel. Autonomous pixel-verification poll is running; if order #1069's conversion lands, I flip the campaign PAUSED → ENABLED automatically.
4. **Two desktop-session tasks queued** for when you open this on the Linux desktop tonight: VPS dashboard deprecation and a 3-commit push (Syncthing sync is in place, GitHub push still blocked by the `criticalmkt` auth mismatch).

---

## Where the ads campaign stands (live state as of EOD)

**Campaign:** `8BL-Shopping-Games` (ID 23766662629)
**Status:** PAUSED (still) — will auto-flip to ENABLED the instant the Purchase pixel verifies.
**Budget:** $22/day (bumped from $20 today)
**Post-promo revert:** scheduled, TrueNAS cron id 661, fires 2026-06-01 00:05 ET → $15/day (idempotent)

### What's guarding the campaign (TrueNAS crons)

| Cron ID | Schedule | Purpose |
|---|---|---|
| 660 | every 2h | `ads_safety_check.py` — pauses on daily $40 or lifetime $50 with 0 conv; auto-recovers from VPS false-trips |
| 661 | 00:05 ET June 1 | `ads_set_budget.py --amount 15` — one-shot revert (idempotent) |
| 663 | 08:00 ET daily | `ads_daily_report_to_navi.py` — stdout of daily report → Navi task |

### What was fixed before flipping

| Item | State |
|---|---|
| Preflight 18/18 green | ✅ verified 10:00 AM ET |
| Shipping threshold $50 | ✅ cowork verified incognito |
| CIB excluded from Shopping ads | ✅ 6,112 variants carry `mm-google-shopping.excluded_destination=["Shopping_ads"]` metafield (propagation 36–48h) |
| $0 test order (for pixel) | ✅ order #1069 placed 5:25 PM ET, cancelled via API (both #1068 + #1069 cancelled, $0 so no refund/restock) |
| Pixel infrastructure fix | ✅ cowork path 2C — G&Y app uninstall+reinstall+migrate-tags; substantive fix per cowork's `docs/cowork-session-2026-04-24-pixel-fix.md` |
| Conversion attribution verified end-to-end | 🟡 **autonomous poll running** — first check 7:31 PM ET, retries every 30 min, cutoff at 9:30 PM ET (4h after order) |

### What I will do autonomously after you log off

1. At 7:31 PM ET, query Ads API for today's Purchase conversion count.
2. If > 0: bump budget (already $22), flip PAUSED → ENABLED via `campaigns:mutate`, log baseline to `docs/launch-log.md`, git commit.
3. If 0: schedule next poll 30 min later. Keep polling until 9:30 PM ET.
4. If still 0 by 9:30 PM: stop. Fix still didn't work. Campaign stays PAUSED. You diagnose in morning.

Check Navi tomorrow morning — the 08:00 ET daily report cron will post either (a) yesterday's perf data if we flipped, or (b) "no campaign activity" if we didn't.

---

## What shipped today (commits)

| Commit | What |
|---|---|
| `b75afce` | render_clip: per-scene crop for multi-camera clips (PERMANENT FIX of yesterday's arcade-shot issue) |
| `efb50a9` | Ads launch prep: consolidated cowork brief + review-seed template |
| `18132ef` | cowork brief: free test order via 100%-off code |
| `5abaa51` | ads: TrueNAS-resident safety check + budget setter |
| `2600bdf` | ads: exclude all 6,112 CIB variants from Shopping ads |
| `9af82f6` | ads: daily report wrapper emits to Navi |
| `ab6972f` | cowork brief: diagnose + fix broken Purchase pixel |
| `ec13c08` | shorts: also post to Facebook Reels |
| `41b1d8a` | cleanup_zernio: match space→underscore URL variants |
| `31cf88d` | Cowork 2026-04-24 pixel-fix session |

12+ commits ahead of `origin/main`. Syncthing syncs everything local across Mac/Linux. **GitHub origin push still blocked by the `criticalmkt` auth mismatch** — `git push` from Linux desktop would clear that if creds are set up there.

---

## Podcast / social — what's queued

8 Ep14 shorts, 4 platforms each (tiktok, youtube, instagram, facebook), all using the new per-scene crop:

| Slot (ET) | Clip | Title |
|---|---|---|
| Sat 09:00 | 03-c2 | God of War Live Action Looks Like a YouTube Skit |
| Sat 13:00 | 03-c3 | Why the Zelda Director Actually Gives Us Hope |
| Sat 19:00 | 05-c1 | Everything Metroid Prime 4 Added Was Bad |
| Sun 09:00 | 05-c2 | PS5 Pro Runs Cyberpunk at 60fps With Full Ray Tracing |
| Sun 13:00 | 05-c3 | Do Not Spend $900 on the PS5 Pro |
| Sun 19:00 | 05-c4 | Buying an Xbox in 2026 Is a Mistake |
| Mon 09:00 | FULL-c1 | Adult Gamers Cant Sit Still Anymore |
| Mon 13:00 | FULL-c2 | Handheld Gaming Is the Adult Gamer Fix |

### Known issue to pull manually if you care

**Today (2026-04-24) went out with duplicates** from earlier reschedule cycles before the cleanup_zernio_queue bug was patched:
- 9 AM ET: `05-c1` (Metroid Prime 4) + `03-c2` (God of War Live Action) both published
- 1 PM ET: `03-c2` (God of War Live Action) AGAIN + `03-c3` (Zelda Director) published
- **The actual duplicate:** `03-c2 "God of War Live Action"` went out at BOTH 9 AM and 1 PM today. Delete the 1 PM version from TikTok/YT/IG if you want to clean it up.

No duplicates in the Sat-onward queue.

---

## Pending for you to pick up tonight on Linux desktop

### 1. VPS dashboard deprecation (operational → visual-only)

Separate brief: **`docs/claude-desktop-brief-2026-04-24-vps-dashboard.md`** — read it first, then execute. Core goal: stop the VPS scheduler jobs so it doesn't fight TrueNAS over ads safety. Dashboard UI stays live as a view-only endpoint.

### 2. Push to GitHub origin

If your Linux desktop has working GitHub creds (not the `criticalmkt` account that's been blocking from Mac), run:

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only      # Syncthing should have everything already; this is a safety check
git push                # 12+ commits to push
```

If it 403s with `criticalmkt` again, we need to wire the right GitHub account before push works from any machine.

### 3. Check on the ads campaign

Before going to bed / in the morning:
- Navi tasklist — should have a daily-report task timestamped tomorrow 8:00 AM ET if the campaign successfully flipped tonight.
- Or pull `docs/launch-log.md` — if I flipped the campaign, baseline is logged there.
- If neither happened by morning, campaign is still PAUSED and pixel still needs diagnosis.

---

## Outstanding (not blocking)

- CIB exclusion metafield propagation — effective 36–48h from ~11:51 AM today → Sunday AM.
- Daily-report cron first real run is tomorrow (Sat) 8:00 AM ET. Until then there's a smoke-test task (`8bit-c2f3ce5a`) in Navi that can be dismissed.
- Post-launch backlog: full Google Merchant Center audit + full 8bitlegacy.com SEO audit (stored in `memory/project_post_launch_todos.md`).

---

## Suggested first action on Linux desktop tonight

```bash
cd ~/Projects/8bit-legacy && git pull --ff-only
cat docs/session-handoff-2026-04-24.md           # this doc
cat docs/claude-desktop-brief-2026-04-24-vps-dashboard.md
```

Then execute the VPS brief. Should be a short session.
