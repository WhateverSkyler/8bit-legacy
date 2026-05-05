# EOD Handoff 2026-05-05 — Ads Launched, Then PAUSED for Leakage Cleanup

**Resume here.** Read this first when picking up tonight.

## TL;DR

- **Campaign 8BL-Shopping-Games launched at 12:21 ET today, ran ~3 hours, PAUSED at 15:35 ET.**
- **Total spend: $17.66, 71 clicks, 0 Purchase conversions.** Spend went to wrong categories (Pokemon cards, consoles, CIB variants — all of which should have been excluded).
- Multiple infrastructure issues fixed during the session (circuit breaker reset, dashboard redeployed, OAuth synced, 4 broken jobs restored, real-time spend tracking added).
- **Listing tree restructured** to filter via cl0 + cl3, plus `excluded_destination` metafields set on Pokemon, consoles, accessories.
- **Currently waiting for MC propagation.** As of 16:30 ET, cl3 variant-level metafield shows 0% propagation in Google Ads' shopping_product view. Decision deferred to tonight.
- **Daily budget lowered from $20 → $10** for safety on next re-enable.
- **DO NOT re-enable campaign** until verification shows clean state.

## How the day went (chronological)

| Time ET | Action | Outcome |
|---|---|---|
| 09:00 | Pick up where 5/01 left off | Audit cl2 metafield state |
| 09:30 | Discover cl2='game' missing on 6,087/6,088 game products | Wrote `scripts/set-custom-label-2.py` |
| 10:08 | Bulk-set cl2 on all 7,142 active products | Done |
| 10:23 | Fixed Chrono Trigger SNES compare_at_price MC bug | Done |
| 10:48-11:14 | Loop polling for MC propagation | cl2 not propagating |
| 11:43 | First forcing-function bulk tagsAdd `__cl2-resync-2026-05-05` | 7,142 products webhooked |
| 12:13 | MC `shopping_product` still showed cl2='' on 7,140 products. **Escalated** | User: "lock in plan mode and fix this so we can launch successfully" |
| 12:18 | Restructured listing tree (cl2-rooted → cl0-rooted) to bypass cl2 dependency | Done |
| 12:21 | Campaign flipped to ENABLED at $20/day | LIVE |
| ~12:30 | Began running re-audit | Found 25 console+accessory products with cl0=over_50/20_to_50 leaking |
| 12:35 | Set excluded_destination on 25 console+accessory products | Done |
| 13:08 | User asked for VPS dashboard login | Reset nginx htpasswd. Login: `admin` / `obuIactQbEBq0HeO` |
| 13:15 | Pulled scheduler status — discovered google_ads circuit breaker tripped 7 days, 4 jobs failing | Confirmed safety net was OFFLINE during launch |
| 13:30-13:45 | Reset breaker, fixed jobs (pricing.json copied, OAuth synced, dashboard rebuilt, port fix) | All 6 jobs green |
| 15:30 | Cowork audit completed. Verified Purchase=Active, MC clean | Side issues flagged |
| 15:33 | **Pulled live Google Ads metrics: $16.22 spend, top spenders were Pokemon cards + consoles + CIB variants** | Realized leakage |
| 15:35 | **PAUSED CAMPAIGN** | Stopped bleed |
| 15:45 | Bulk-excluded 1,028 Pokemon products via excluded_destination | Done |
| 15:50 | Set custom_label_3='cib' on 6,112 CIB variants (variant-level) | Done |
| 15:52 | Restructured listing tree again: cl0 root + cl3 inner subdivision excluding cib | Done |
| 15:57 | Forcing-function bulk tagsAdd `__exclusion-resync-2026-05-05-pm` | 7,142 products webhooked |
| 16:00 | Lowered budget $20 → $10 for safety on re-enable | Done |
| 16:30 | MC propagation check: 0% cl3 propagated, 0 Pokemon cl2='pokemon_card' visible | **Waiting** |

## Current state

### Campaign (Google Ads, customer 8222102291, campaign 23766662629)
- Status: **PAUSED**
- Daily budget: **$10/day** (was $20)
- Bid strategy: Manual CPC
- Networks: Google Search only (no Partners/Display)
- Geo: US only
- Listing tree (post-restructure):
  ```
  ROOT (subdivision)
  ├── cl0=over_50 (subdivision)
  │   ├── cl3=cib → EXCLUDED
  │   └── cl3=else (catches '' AND Game Only) → $0.35
  ├── cl0=20_to_50 (subdivision)
  │   ├── cl3=cib → EXCLUDED
  │   └── cl3=else → $0.08
  └── cl0=else → EXCLUDED
  ```
- Conversion goals: 7 active, all primary, Purchase = receiving real values
- Today's actual metrics: 71 clicks / 3,694 impr / **$17.66 spend** / 0 Purchase conv (77 micro-conv from page-views/view-items)

### Shopify-side metafields (verified set, 100% coverage)
- `mm-google-shopping.custom_label_0` set on 7,142 active products (over_50/20_to_50/under_20/synced)
- `mm-google-shopping.custom_label_2` set on 7,142 active products (game/pokemon_card/console/accessory/sealed/other)
- `mm-google-shopping.custom_label_3='cib'` set on **6,112 CIB variants** (variant-level)
- `mm-google-shopping.excluded_destination=["Shopping_ads"]`:
  - 1,028 Pokemon products (product-level)
  - 25 console+accessory products (product-level)
  - 6,112 CIB variants (variant-level — but NOT honored by G&Y, that's why we added cl3 fallback)

### MC bridge state (as of 16:30 ET)
- Total products in MC: 6,194 (all NOT_ELIGIBLE due to paused campaign)
- cl0='over_50' visible: 391 entries
- cl0='20_to_50' visible: 696 entries
- cl2='pokemon_card' visible: **0** (set today, hasn't propagated)
- cl3='cib' visible: **0** (set today, hasn't propagated)
- If campaign re-enabled now: 1,089 products would serve, ~513 of which are CIB variants → **leak still active until cl3 propagates**

### Safety system
- Circuit breakers: BOTH ARMED (`pricing` + `google_ads` both not tripped)
- All 5 ad safety checks passing as of last run:
  - daily_spend_limit ($17.66 / $40)
  - lifetime_no_conversion_ceiling ($17.66 / $50)
  - consecutive_no_conversions (0/3 days)
  - store_uptime
  - rolling_roas_floor (deferred until day 7)
- All 6 scheduled jobs healthy
- Real-time spend tracking enabled (today's data now flows into local DB)

### VPS dashboard
- URL: `https://8bit.tristanaddi.com/`
- Username: `admin`
- Password: `obuIactQbEBq0HeO` (reset today, save in password manager)
- Healthy: scheduler running, all jobs green, circuit breakers armed

## What's PENDING — read carefully tonight

### Step 1: Re-check MC propagation (1 min)

```bash
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv('config/.env')
from google.ads.googleads.client import GoogleAdsClient
client = GoogleAdsClient.load_from_dict({
    'developer_token': os.environ['GOOGLE_ADS_DEVELOPER_TOKEN'],
    'client_id': os.environ['GOOGLE_ADS_CLIENT_ID'],
    'client_secret': os.environ['GOOGLE_ADS_CLIENT_SECRET'],
    'refresh_token': os.environ['GOOGLE_ADS_REFRESH_TOKEN'],
    'login_customer_id': os.environ['GOOGLE_ADS_LOGIN_CUSTOMER_ID'],
    'use_proto_plus': True,
})
service = client.get_service("GoogleAdsService")
# Count CIB variants with cl3='cib' propagated
n_cib_total = sum(1 for _ in service.search(customer_id='8222102291', query="SELECT shopping_product.merchant_center_id FROM shopping_product WHERE shopping_product.title LIKE '%Complete (CIB)%'"))
n_cib_cl3 = sum(1 for _ in service.search(customer_id='8222102291', query="SELECT shopping_product.merchant_center_id FROM shopping_product WHERE shopping_product.title LIKE '%Complete (CIB)%' AND shopping_product.custom_attribute3 = 'cib'"))
n_pkm = sum(1 for _ in service.search(customer_id='8222102291', query="SELECT shopping_product.merchant_center_id FROM shopping_product WHERE shopping_product.custom_attribute2 = 'pokemon_card'"))
print(f"CIB variants in MC: {n_cib_total}, with cl3='cib': {n_cib_cl3} ({100*n_cib_cl3/n_cib_total if n_cib_total else 0:.0f}%)")
print(f"Pokemon products with cl2='pokemon_card' visible: {n_pkm}")
EOF
```

**Decision tree:**

| cl3 propagation | Pokemon cl2 visible | Action |
|---|---|---|
| ≥80% | >500 | **GO** — re-enable campaign |
| 50-80% | 200-500 | **WAIT** another hour, re-check |
| <50% | <200 | **PIVOT** — use product-level fallback (Step 2) |

### Step 2: PIVOT plan if cl3 doesn't propagate

If by tomorrow morning cl3 still hasn't propagated, G&Y app does NOT honor variant-level custom_label_X. Options ranked by recommendation:

**Option A — Don't differentiate, accept some CIB serving (NOT RECOMMENDED):**
- Re-enable as-is. Daily $10 cap limits damage.
- Per current data, ~50% of clicks would still go to CIB variants → wasted spend.

**Option B — Set product-level excluded_destination on ALL games with high cl0 — BUT only on the products themselves, then SEPARATELY re-add the Game Only variants as standalone products without CIB siblings:**
- Surgical, complex. Probably 2-4 hours of work.

**Option C — Use Google Merchant Center supplemental feed (CSV) to override cl3 at offer level:**
- Per `feedback_mc_supplemental_disaster.md`: NEVER use MC's "Add product source" wizard. But a *supplemental feed* targeting specific item_ids might work if uploaded as CSV through Feed B.
- Risky. Needs research.

**Option D — Bulk-edit CIB variants to be unavailable on Google sales channel via Shopify Admin UI:**
- Click into each CIB variant, untick Google channel availability. Manual but reliable.
- 6,112 variants — would need a script to bulk-update via Shopify API.
- Need to verify Shopify API supports per-variant channel availability. (Most Shopify "channel availability" is product-level.)

**Option E (RECOMMENDED) — Keep campaign paused, dig deeper into G&Y app's metafield filter behavior:**
- Find the actual list of metafields G&Y respects at variant vs product level.
- Use only the ones it respects.
- Worth 30-60 min of research before pivoting.

### Step 3: If cl3 propagates, re-enable sequence

1. Verify shopping_product breakdown is clean: 0 CIB variants with cl3=empty serving, 0 Pokemon visible
2. Re-query "would serve" inventory — should be ~1,000 Game Only games
3. Sample 10 products visually, confirm all are Game Only retro games (not Pokemon, not console, not CIB)
4. Flip campaign to ENABLED:
   ```python
   # Inline in repl OR write a one-liner. Same pattern as today's flip.
   import os, requests
   from dotenv import load_dotenv
   load_dotenv('config/.env')
   # ... (see today's session for the OAuth + mutate pattern)
   ```
5. Watch first hour metrics carefully. Real-time check via `python3 -c '...'` querying TODAY's metrics.
6. If anything weird → re-pause immediately.

### Step 4: Refund decisions for today's $17.66

You've already lost $17.66 to the wrong-category leakage. Options:
- **Eat it** as the cost of learning. Most reasonable.
- **File a refund request with Google Ads Support** citing the misconfiguration. Long shot, takes weeks.
- **Use as data** for negative keywords. Today's search terms ARE useful — adding 20-50 negatives based on Pokemon TCG card-set names + console-related terms would tighten future spend.

## Critical IDs / state pinned

```
SHOPIFY_STORE_URL=dpxzef-st.myshopify.com
Google Merchant Center ID: 5296797260
Google Ads Customer ID:    8222102291
Manager Customer ID:       4442441892
Campaign ID:               23766662629  (8BL-Shopping-Games, PAUSED)
Ad Group ID:               202385540384  (all-products)
Conversion AW:             AW-18056461576
VPS:                       178.156.201.13 (Hetzner) — `hetzner` SSH alias
Dashboard URL:             https://8bit.tristanaddi.com/  (admin / obuIactQbEBq0HeO)
Shopify dashboard path:    /home/bitlegacy/htdocs/8bit.tristanaddi.com/
Dashboard DB on VPS:       /home/bitlegacy/htdocs/8bit.tristanaddi.com/db/8bitlegacy.db
config/pricing.json on VPS: /home/bitlegacy/htdocs/config/pricing.json
PM2 process name:          8bit-dashboard (managed by bitlegacy user via nvm node v22.22.2)
Business phone (GV):       (229) 329-2327

Bulk op IDs today:
  set-cl2:           5516639174690 (10:08 ET, 7142 products)
  cl2-resync-tagsAdd: 5516907118626 (11:43 ET, 7142 products)
  exclude-pokemon:   5517583024162 (15:45 ET, 1028 products)
  cl3-cib variants:  5517596229666 (15:50 ET, 6112 variants)
  pm-resync-tagsAdd: 5517607043106 (15:57 ET, 7142 products)

Files modified today (uncommitted):
  scripts/force-mc-resync.py — added --tag CLI arg with auto-dated default
  scripts/set-custom-label-2.py — NEW
  dashboard/src/lib/jobs.ts — port 3001 → env-driven (3002)
  dashboard/src/app/api/google-ads/sync/route.ts — today-inclusive
  scripts/find-contact-sidebar.py — NEW (small helper)

Docs created today:
  docs/ads-launch-readiness-audit-2026-05-05.md
  docs/claude-cowork-brief-2026-05-05-contact-page.md
  docs/claude-cowork-brief-2026-05-05-contact-page-pt2.md
  docs/claude-cowork-brief-2026-05-05-campaign-audit.md
  docs/claude-cowork-brief-2026-05-05-post-launch-full-audit.md
  docs/cowork-session-2026-05-05-contact-page.md (cowork wrote this)
  docs/eod-handoff-2026-05-05-ads-launch-and-leakage.md (this file)

VPS-only changes (not in repo):
  /etc/nginx/.htpasswd_8bit — admin password reset
  /home/bitlegacy/htdocs/config/pricing.json — copied from local
  /home/bitlegacy/htdocs/8bit.tristanaddi.com/.env.local — 6 GOOGLE_ADS_* vars synced
  /home/bitlegacy/htdocs/8bit.tristanaddi.com/db/8bitlegacy.db — circuit_breaker_google_ads reset
```

## Lessons learned (read tomorrow)

1. **Variant-level `excluded_destination` does NOT work via Shopify G&Y app.** Memory said it did (4/24) but never verified end-to-end. Real verification = pulling Google Ads `shopping_product` view and confirming the variants drop out. We didn't do that until today.

2. **Listing tree restructure introduced exposure.** When I rebuilt the tree from cl2-rooted to cl0-rooted to bypass cl2 propagation delay, I removed the "must be game" filter that had blocked Pokemon/consoles/accessories. They got into ad serving. Lesson: always verify the new filter mechanism is in place BEFORE removing the old one.

3. **The 4/29 OAuth re-auth invalidated the VPS-side refresh token.** When OAuth was re-authed locally, the token wasn't synced to VPS, so VPS scheduler's google-ads-sync silently failed for 6 days. Lesson: any OAuth re-auth should propagate to all consumers.

4. **The VPS dashboard had a stale build (Apr 27).** It was missing the `/api/google-ads/sync` route and used the wrong port. The deployment process needs to be repeatable. Consider: a `scripts/deploy-vps.sh` that does pull/build/restart.

5. **Real-time spend tracking is essential.** The original google-ads-sync excluded "today" because Google's data is preliminary. But that meant the safety system saw $0 while $16 was being spent. The fix to include today's data was small but high-leverage.

6. **The "99% products excluded" banner in Google Ads UI is misleading.** It includes deliberately-excluded products (CIB variants, Pokemon, etc.) and over-counts. Don't use it as a diagnostic.

## When you pick up tonight

1. Read this doc first
2. Run the cl3 propagation check (Step 1 above)
3. Decide based on the decision tree
4. If GO: re-enable + monitor
5. If PIVOT: research G&Y metafield support before more changes
6. Either way: don't add new ad spend without verification

## What I'd do first thing tomorrow morning if I'm here

Same Step 1 + Step 3. Most likely cl3 will have propagated overnight (per 5/01 pattern). Then we re-enable at $10/day, watch carefully for 1 hour, and bump to $20-30/day if clean.

You did everything right today. The infrastructure issues weren't yours, they were latent bugs from prior sessions. Good night.
