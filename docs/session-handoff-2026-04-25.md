# Session Handoff — 2026-04-25 EOD

**Previous:** `docs/session-handoff-2026-04-24-night.md`
**Resume target:** next session, any machine.

---

## TL;DR

A long Saturday session that swept up a lot of accumulated bugs:

1. **Photo cadence is fixed** — all 26 photo posts on the IG/FB Tue/Thu/Sat
   12:00 ET schedule were stuck in Zernio `draft` instead of `scheduled`.
   Rebuilt the queue (delete + re-upload + re-create) and confirmed today's
   `heatran_pkmn` and rolled-forward `gamecube_and_wii_TP` both posted live.
   Cadence runs clean Tue/Thu/Sat through 2026-06-18.
2. **Shorts dup spam from earlier in the week** is bounded — user deleted the
   surviving copies off TikTok/YT/IG/FB manually leaving only one God of War
   short per platform. Saved a `feedback_shorts_blocklist` memory so
   `schedule_shorts.py` never re-uploads `03-c2` (God of War Live Action).
3. **Shorts captions now lead with a stylized title** (YouTube-style 4-7
   word hot take) above the hashtag block. Code change in
   `scripts/podcast/schedule_shorts.py`; 7 already-scheduled Zernio posts
   backfilled.
4. **Pokemon catalog cleaned up** — 148 sub-$2 Pokemon cards (guaranteed-loss
   listings) drafted in Shopify; importer default `--min-price` 0 → 5.0;
   `pokemon_cards` multiplier 1.15 → 1.25 in `config/pricing.json`. Saved a
   `project_ebay_resale_exemption` memory flagging multi-state eBay sales
   tax exemption as a high-priority profit leak for the roadmap.
5. **Discount cleanup** — 3 lingering test discounts (auto free-shipping +
   two TESTZERO codes) deleted by cowork, verified clean storefront. Commit
   `5e00017`.
6. **Pixel verification: NEGATIVE.** Cowork checked the Ads UI Webpages tab
   for "Google Shopping App Purchase" and ALL 7 G&Y conversion actions show
   0 count over "All time," including Page View. Yesterday's 2C
   uninstall+reinstall+migrate-tags fix did not resolve it. Campaign stays
   PAUSED. Real customer order #1070 ($146.92, placed 10:49 ET, profit
   $18.57 after fees) was the test that confirmed the failure.

---

## What shipped today (commits)

| Commit | What |
|---|---|
| `5e00017` | Cowork session: discount cleanup + pixel verification (cowork-authored, on origin) |
| _pending_ | This session's day-of fixes (Pokemon, photos, shorts captions, EOD doc) |

The cowork commit was pushed to origin successfully — the `criticalmkt`
auth issue from prior sessions seems to have been resolved (likely the GitHub
identity is now set up correctly on whichever machine cowork ran from).

---

## Real order #1070 — first revenue since the recent price work

| Field | Value |
|---|---|
| Order | `#1070` |
| Placed | 2026-04-25 10:49 ET |
| Total | $146.92 |
| Fees (Shopify) | ~$4.56 (2.9% + $0.30) |
| Net to seller | ~$142.36 |
| Cost basis (eBay sourcing) | ~$123.79 |
| **Profit** | **~$18.57** |
| Line items | Tekken 3 (PS1 game-only), Monster Lab (PS2 game-only), Lucario ex (82/142) Stellar Crown |

User flagged ONE Pokemon line as a small loss in this order: a Lucario
listed at $1.99 (~$2.50 eBay LP cost) — that's the same structural problem
the catalog audit revealed. Drafted in this session.

---

## Pokemon catalog — what changed

**Before:** 1,568 active Pokemon products. **478** under $5 list price
(margin-risk zone). **148** under $2 = guaranteed loss after Shopify fees.

**After this session:**
- 148 sub-$2 cards set to status=DRAFT (de-listed but not deleted; can be
  re-activated if pricing improves). See `scripts/draft-sub2-pokemon.py` —
  one-shot, idempotent, supports `--apply` flag.
- `scripts/pokemon-card-importer.py` default `--min-price` changed 0 → 5.0
  (matches the floor specified in `CLAUDE.md`).
- `config/pricing.json` `pokemon_cards` multiplier 1.15 → 1.25 (TCGPlayer
  mid often runs 15-25% below real eBay LP cost; 1.15x was structurally too
  thin).

**Still unaddressed (worth a future pass when you have time):**
- 130 cards listed at $2.00-$2.99 (break-even at best) — kept live for now,
  but consider another draft sweep if margin reports show them losing.
- 84 cards at $3.00-$3.99 and 116 at $4.00-$4.99 — surface profit margins
  vary; only cull if eBay LP cost exceeds the breakeven for that price tier.

---

## Photo schedule — what happened and what's next

**Failure mode found:** all 26 photos uploaded by `schedule_photos.py` on
2026-04-19 ended up `status=draft` in Zernio rather than `scheduled`. Only
the first one (`3ds games.png`) actually published, on 2026-04-21. The rest
sat as drafts and silently missed their slots starting 2026-04-23.

**Theory:** stale presigned-upload URLs. Zernio's `POST /posts` returns a
`/temp/<filename>` media URL that gets promoted to `/media/<filename>` only
on first publish; if the post never publishes by some internal Zernio
deadline, the URL goes 404 and the post is orphaned to draft. Updating
`status` via PUT does not promote drafts back to scheduled — Zernio rejects
it silently.

**Fix applied:** delete each draft, re-upload the source PNG, re-create the
Zernio post with the same `scheduledFor`. Fresh creates land as `scheduled`.
Done for 24 of 26 (3ds_games already published; gamecube auto-published
because its rebuild used a past `scheduledFor` of 2026-04-23).

**Side effect:** today (2026-04-25) ended up with TWO photo posts on IG/FB
— `gamecube_and_wii_TP` (~12:01 ET, retroactive) and `heatran_pkmn`
(~12:01 ET, the intended slot). User chose to leave both up rather than
manually delete from socials.

**No repeat-protection in code yet.** If `schedule_photos.py` is re-run on a
fresh photo batch and the same Zernio bug recurs, this same delete +
re-upload + re-create dance will be needed. Considered patching
`schedule_photos.py` to send `status: "scheduled"` explicitly in the create
payload, but Zernio's POST already creates as `scheduled` for fresh uploads;
the bug only emerged for posts that sat unpublished long enough for the
presigned URL to expire. If it recurs, see `scripts/inspect-zernio-queue.py`
for a quick "what state is each post in" visualization.

**Cadence currently scheduled:**
- Already published: 4/21 (3ds), 4/25 (gamecube + heatran)
- Tue 4/28 onward: 24 photos at 12:00 ET on Tue/Thu/Sat through 2026-06-18
- After 6/18 you'll need fresh photos in `data/social-media/final/` to keep
  the cadence going. Worth queuing a new batch by mid-June.

---

## Shorts — captions now have titles

**Before:** captions were hashtag-only (`#fyp #foryoupage ... #shorts`).

**After:** captions are `<Stylized Title>\n\n<hashtags>`. Title pulled from
each clip's `title` field in the clip plan. Capped at 70 chars.

**Code:** `scripts/podcast/schedule_shorts.py` `_caption_for(spec)`.

**Backfilled:** 7 already-scheduled Zernio posts (today 13:00 → 4/27 13:00)
got their content updated via PUT to add the title prefix.

**Blocklist memory:** `feedback_shorts_blocklist.md` — `03-c2` (God of War
Live Action) must never be re-scheduled. User manually deleted the dups off
all platforms; the one surviving God of War copy stays.

---

## Pixel — what we know now

**Symptom:** ALL 7 Google Shopping App conversion actions show 0 count over
"All time" — Purchase, Page View, View Item, Add To Cart, Begin Checkout,
Add Payment Info, Search. Cowork verified via the Ads UI Webpages tab,
which is the authoritative read (GAQL doesn't surface fired-but-unattributed
events).

**Diagnosis narrowed:** because Page View is also 0, the Google & YouTube
tag isn't loading on the storefront at all. This is broader than a
thank-you-page-specific gate. Yesterday's 2C path (uninstall + reinstall +
migrate Google tags) did not resolve.

**Next-pass diagnostics (queued for next cowork session):**

1. Confirm MonsterInsights is fully removed — both as an installed app and
   from `theme.liquid` / Custom Pixel registrations. Even after the
   2026-04-24 migration made G&Y the "canonical" Google tag owner, MI may
   still be loading in parallel and intercepting the conversion linker.
2. Complete the **Online Store contact-info confirmation** gate inside the
   Google & YouTube app onboarding. Cowork's 4/24 session noted this was
   still pending and could be blocking full tag dispatch.
3. Install **Google Tag Assistant Companion**, place a real test order with
   DevTools open on the storefront tab AND the thank-you redirect, capture
   exactly which `gtag` events fire.
4. Verify the URL-match rule on `Google Shopping App Purchase` includes the
   modern Shopify checkout-extensibility path (`/checkouts/c/.../thank_you`)
   — Shopify migrated this URL shape recently and the rule may still point
   at the legacy path.

**No spend in the meantime.** Campaign `8BL-Shopping-Games` stays PAUSED.
TrueNAS safety crons are still running but have nothing to safeguard.

---

## Memory updates

| File | What |
|---|---|
| `feedback_shorts_blocklist.md` | New. Don't re-schedule `03-c2`. |
| `project_ebay_resale_exemption.md` | New. Multi-state resale cert is a real profit leak; defer until volume justifies. |
| `MEMORY.md` | Index updated for both. |

---

## Outstanding (carryover from previous handoffs)

- **VPS dashboard scheduler deprecation** — still open. SSH alias `hetzner`
  works on Linux desktop. Brief at
  `docs/claude-desktop-brief-2026-04-24-vps-dashboard.md`. TrueNAS auto-recovers from any VPS false-trips, so not urgent.
- **Pixel diagnosis pass 2** — see "Pixel" section above.
- **Audio podcast distribution** — Spotify/Apple host pick still pending
  (memory `project_audio_distribution.md`).
- **Post-launch backlog** — full Merchant Center audit + 8bitlegacy.com SEO
  audit (memory `project_post_launch_todos.md`). Blocked on ad launch which
  is blocked on pixel.

---

## Files / scripts added this session

- `scripts/cleanup-test-discounts.py` — listed but couldn't delete (token
  scope). Cowork did the manual delete instead.
- `scripts/inspect-zernio-queue.py` — useful for future Zernio queue audits.
- `scripts/draft-sub2-pokemon.py` — one-shot, used. Re-runnable.
- `docs/claude-cowork-brief-2026-04-25-discount-cleanup.md` — superseded
  in-flight by the combined one cowork actually used; kept for history.
- `docs/claude-cowork-brief-2026-04-25-cleanup-and-pixel.md` — the brief
  cowork executed.
- `docs/cowork-session-2026-04-25-cleanup-and-pixel.md` — cowork's handoff.
- `docs/launch-log.md` — appended pixel-verification-failed section.
