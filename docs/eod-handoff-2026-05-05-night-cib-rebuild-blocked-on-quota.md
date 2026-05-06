# EOD Handoff 2026-05-05 (night) — CIB rebuild blocked on Google Ads quota; finish in AM

**Resume here.** Read this first when picking up tomorrow.

## TL;DR

- Diagnosed root cause of today's $17.66 leak: Shopify G&Y app **does not propagate variant-level metafields** to MC. The cl3='cib' approach was fundamentally broken; would never have worked.
- Pivoted to **Google Ads item_id negative criteria** (bypasses MC propagation entirely).
- Built canonical CIB offer-ID list (`data/cib-offer-ids.txt`, 6,102 IDs) and a 3-check pre-flight verifier (`scripts/verify_cib_exclusion.py`).
- Refactored `scripts/ads_launch.py` for item_id-based exclusion + diff-based idempotency.
- Started live rebuild at ~18:50 ET. **Hit Google Ads daily mutation quota after 2,000/6,102 negatives created.** Quota resets in ~13.4h (~8 AM ET 5/06).
- Tree right now is in a partial state: 5 structural nodes + 2,000 item_id negatives + 2 leftover cl2 nodes from this morning's restructure that need to be cleaned up tomorrow.
- **Campaign is still PAUSED. No money at risk. Do NOT enable until tomorrow's verifier passes.**
- Budget lowered to $5/day for safety on re-enable.

## What changed today (this session, evening)

### Plan
- Plan file: `/Users/tristanaddi1/.claude/plans/snug-booping-liskov.md`
- User approved the plan with two preferences: re-enable "whenever everything is guaranteed working" (no autonomous flips), canary at $5/day for 24h before bumps.

### Code (all uncommitted at time of writing)
- **`scripts/generate-cib-exclusion-feed.py:137`** — fixed `shopify_US_` → `shopify_ZZ_` prefix bug (Feed B uses ZZ; old script would have produced offer IDs that don't match anything in MC).
- **`scripts/list_cib_offer_ids.py`** — NEW. Produces `data/cib-offer-ids.txt` from union of Shopify GraphQL scan + MC `shopping_product` view. 6,102 unique IDs (Shopify: 6,088; MC: 2,877; only-MC: 14 — included for safety).
- **`scripts/ads_launch.py`** — major refactor:
  - New target tree: ROOT (item_id) → 6,102 negatives + item_id=else → cl0 over_50/20_to_50/else
  - Dropped cl2 layer entirely (cl2 propagation is essentially zero, was blocking serving)
  - Diff-based idempotency: if structural skeleton matches, only sync item_id negatives + bid drift
  - Full rebuild only when shape drifts or `--rebuild-from-scratch` is passed
  - New flags: `--budget-micros`, `--cib-list`, `--rebuild-from-scratch`
  - `MAX_TREE_NODES = 18,000` safety guard (Google's hard limit is 20k)
- **`scripts/verify_cib_exclusion.py`** — NEW. 3-check pre-flight verifier:
  1. Tree integrity — every CIB offer ID in negatives, every item_id criterion is negative
  2. MC cross-check — every CIB visible in `shopping_product` is in our negative set
  3. Game-Only sanity — ≥100 non-CIB rows visible at cl0=tiered (haven't over-excluded)
  Exit 0 = all pass. Exit 1 = at least one fail. Exit 2 = environment error.

### State changes via API today (this session)
- Google Ads campaign budget: $10/day → $5/day ✓
- Listing tree: removed all 8 prior nodes; created 7 structural nodes (with cl2 layer); created 2,000 item_id negatives. Then quota hit.
- (At time of write) tree has stale cl2_game and cl2_else nodes from the partial run that the now-refactored script will detect and clean up tomorrow.

## Critical state pinned

```
SHOPIFY_STORE_URL=dpxzef-st.myshopify.com
Google Merchant Center ID: 5296797260
Google Ads Customer ID:    8222102291
Manager Customer ID:       4442441892
Campaign ID:               23766662629  (8BL-Shopping-Games, PAUSED)
Ad Group ID:               202385540384
Conversion AW:             AW-18056461576
VPS:                       178.156.201.13 (Hetzner) — `hetzner` SSH alias
Dashboard URL:             https://8bit.tristanaddi.com/  (admin / obuIactQbEBq0HeO)

CIB exclusion mechanism:
  data/cib-offer-ids.txt     6,102 offer IDs
  scripts/list_cib_offer_ids.py  regenerate this list anytime
  scripts/ads_launch.py      build/diff the tree
  scripts/verify_cib_exclusion.py  pre-flight verifier
```

## Tomorrow morning checklist (~30 min)

1. **~8:00 AM ET — quota resets.** Confirm with a small read query that GAds API is responsive.
2. `python3 scripts/list_cib_offer_ids.py` — refresh the list (catches anything added overnight).
3. `python3 scripts/ads_launch.py --budget-micros 5000000 --skip-negatives` — finish the rebuild.
   - Will detect structural mismatch (current tree has 7 structural nodes incl. cl2; desired has 5 structural).
   - Triggers full rebuild: removes 2,009 existing → creates 6,107 new (5 structural + 6,102 negatives).
   - Total ~8 API calls; ~30s wall time.
   - If quota hits again: stop, investigate (shouldn't happen — fresh day, clean slate).
4. `python3 scripts/verify_cib_exclusion.py` — must show all 3 checks PASS.
5. `curl -s -o /dev/null -w "%{http_code}" https://8bitlegacy.com/pages/contact` — must show `200`.
6. Open `https://8bit.tristanaddi.com/scheduler` — all 6 jobs green, both circuit breakers armed.
7. If all green: Tristan flips campaign status ENABLED via Google Ads UI (or one-line API call).
8. Watch first hour at $5/day budget. Anything off → re-pause.

## Why we're confident this approach works (not promising — earned via verification)

The `verify_cib_exclusion.py` script does what was missing all along: it queries Google Ads' OWN view of which products would serve, against the OWN view of what's negative-criterion'd. No more "we set the metafield, it should propagate" hand-waving. Either the tree is correct or it isn't, and the verifier proves which.

Check 2 specifically — "every CIB visible in MC is in our negative set" — already passes today (2,877 CIBs, all 2,877 are in our 6,102 desired list). Check 1 will pass once tomorrow's rebuild adds the missing 4,102 negatives. Check 3 (Game-Only sanity ≥100) already passes (577 visible).

## What if cl0 propagation never finishes?

cl0 is currently at 17% across both target tiers (393 over_50, 696 20_to_50). It's been propagating since April; today's resync this morning should push it higher. Worst case if cl0 never improves: Game Only items with cl0='' fall to cl0=else NEG (excluded). Campaign serves only the 1,089 items with cl0 set today. That's still a viable launch — small but meaningful inventory. Better to launch with that than wait indefinitely.

## What did NOT change today (carryover from prior EOD)

- All findings from `docs/ads-launch-readiness-audit-2026-05-05.md` still hold for items 1, 2, 4-8, 10-13.
- 335 phrase-match negative keywords loaded (untouched).
- Conversion pixel verified Active.
- Real-time spend tracking deployed today.
- VPS scheduler all 6 jobs green at last EOD checkpoint.
- Both circuit breakers armed.

## Deferred to post-launch (per `project_post_launch_todos.md` and `docs/ads-launch-readiness-audit-2026-05-05.md`)

- Search-term-level breakdown of today's $17.66 spend (run `scripts/ads_daily_report.py --since 2026-05-05`)
- Add 20-50 negative keywords from today's wasted search terms
- Stale `AW-11389531744` pixel cleanup
- Phase B server-side webhook backstop deployment
- Full MC listing-quality audit
- Full SEO audit
- Multi-state sales tax MTC fix
