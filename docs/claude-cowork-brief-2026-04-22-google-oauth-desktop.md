# Claude Cowork Brief — 2026-04-22 — Google Ads OAuth (Desktop client)

## The task in one sentence
Create a new **Desktop-type** OAuth 2.0 client in the GCP project that owns the current Google Ads API credentials, swap it into `config/.env` + `dashboard/.env.local`, mint a fresh refresh token, verify it works, push.

## Why this matters
Google Ads API calls are currently blocked — every token exchange returns `{"error": "invalid_grant"}`. Ads campaign launch is stalled on this one fix. Previous cowork cycles deferred it because the existing OAuth client is "Web" type and won't accept `http://localhost:<dynamic-port>` redirects, which the standard InstalledAppFlow requires. **You are the third cycle to get this task — finish it this time.** The local-machine human has already attempted the reauth and hit `redirect_uri_mismatch`. A Desktop OAuth client side-steps redirect URI registration entirely (it accepts any localhost port).

## Prerequisites you already have
- GCP console access via the signed-in browser profile (Google account: `tristanaddi1@gmail.com`)
- Shell + file write access to the repo
- `config/.env` is present with the current stale creds

## Steps

### 1. Identify the correct GCP project
The existing Web OAuth client has client ID prefix **`585154028800-30b12ji9qdncj1ng4lv8f8i3atnafce9`**. The project number is the first segment: **`585154028800`**.

In https://console.cloud.google.com/ — switch to that project (project number 585154028800). Do NOT create a new project.

### 2. Create a Desktop OAuth client
1. Go to https://console.cloud.google.com/apis/credentials (make sure you're in project 585154028800)
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Application type: **Desktop app** (critical — NOT "Web application")
4. Name: `8-Bit Legacy Ads Desktop`
5. Click **Create**
6. From the resulting dialog, capture both:
   - `client_id` (ends in `.apps.googleusercontent.com`)
   - `client_secret`

### 3. Swap credentials into both .env files
Edit these two files in-place, replacing ONLY the `GOOGLE_ADS_CLIENT_ID` and `GOOGLE_ADS_CLIENT_SECRET` lines:
- `config/.env`
- `dashboard/.env.local`

Do NOT touch any other keys (especially `GOOGLE_ADS_DEVELOPER_TOKEN` and `GOOGLE_ADS_CUSTOMER_ID`/`LOGIN_CUSTOMER_ID`).

### 4. Mint a fresh refresh token
The reauth script is ready at `scripts/google_ads_reauth.py`. It already passes `prompt=consent&access_type=offline` (required — without both, Google returns no refresh token or re-issues a stale one).

Run:
```bash
cd ~/Projects/8bit-legacy
python3 scripts/google_ads_reauth.py
```

The script prints a consent URL and listens on a random localhost port. Open the URL in the signed-in browser, click **Allow**. Google will redirect to `http://localhost:<port>/?code=...`; the script catches it and writes the new refresh token into both env files.

**Expected terminal output on success:**
```
✓ Got refresh token: 1//04_...
✓ patched /root/Projects/8bit-legacy/config/.env
✓ patched /root/Projects/8bit-legacy/dashboard/.env.local
```

### 5. Verify the token is live
```bash
set -a; source ~/Projects/8bit-legacy/config/.env; set +a
curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=$GOOGLE_ADS_CLIENT_ID" \
  -d "client_secret=$GOOGLE_ADS_CLIENT_SECRET" \
  -d "refresh_token=$GOOGLE_ADS_REFRESH_TOKEN" \
  -d "grant_type=refresh_token" | python3 -m json.tool
```

**Success criteria:** response contains `"access_token": "ya29...."` AND `"expires_in": 3599`. NOT `invalid_grant`.

### 6. Verify Ads API actually works end-to-end
Not just the token exchange. Pick the simplest Google Ads call we have — a GAQL read against the customer. If there's a small diagnostic script in the repo, run it; otherwise:

```bash
python3 - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv("config/.env")
from google.ads.googleads.client import GoogleAdsClient
cfg = {
    "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id":       os.environ["GOOGLE_ADS_CLIENT_ID"],
    "client_secret":   os.environ["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token":   os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or os.environ.get("GOOGLE_ADS_MANAGER_ID"),
    "use_proto_plus": True,
}
client = GoogleAdsClient.load_from_dict(cfg)
svc = client.get_service("GoogleAdsService")
cid = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
resp = svc.search_stream(customer_id=cid, query="SELECT customer.descriptive_name FROM customer LIMIT 1")
for batch in resp:
    for row in batch.results:
        print("OK:", row.customer.descriptive_name)
PY
```

**Success criteria:** prints `OK: <account name>` (likely "8-Bit Legacy" or similar). If instead you get `CUSTOMER_NOT_FOUND`, `USER_PERMISSION_DENIED`, or any Google Ads API error — STOP and report it, do NOT proceed to step 7.

### 7. Commit + push
```bash
# Do NOT commit .env files — both are gitignored (verify with `git check-ignore config/.env dashboard/.env.local` before committing anything).
git add -A
git status                              # verify no .env files are staged
git commit -m "Rotate Google Ads OAuth to Desktop client (unblocks API)"
git push
```

### 8. Update the dashboard on the VPS
The dashboard at `8bit.tristanaddi.com` also reads `GOOGLE_ADS_CLIENT_ID/SECRET/REFRESH_TOKEN` from its local `dashboard/.env.local`. SSH creds / process manager details are in `docs/vps-dashboard-status-2026-04-10.md` and memory `project_vps_dashboard.md`. Pull the repo, overwrite `dashboard/.env.local` with the fresh Ads creds only (do NOT clobber other keys), and restart the dashboard process.

If VPS access is not configured in this cowork environment, SKIP this step and emit a Navi task (see scripts/navi_alerts.py) saying: "VPS dashboard still needs fresh Google Ads creds — pull repo + update `.env.local` + restart".

### 9. Write a handoff
Append a section to `docs/session-handoff-2026-04-22.md` (create if missing) titled "Google Ads OAuth rotation" containing:
- New client_id prefix (first 20 chars + last 4 — NOT the full secret)
- Whether VPS was updated
- The `OK: <account name>` from step 6

Push the handoff.

## What success looks like
- [ ] Desktop OAuth client created in project 585154028800
- [ ] `config/.env` + `dashboard/.env.local` have new `GOOGLE_ADS_CLIENT_ID` + `GOOGLE_ADS_CLIENT_SECRET` + `GOOGLE_ADS_REFRESH_TOKEN`
- [ ] Step 5 returns `access_token`, not `invalid_grant`
- [ ] Step 6 returns `OK: <name>`
- [ ] Commit pushed (no .env files in the diff)
- [ ] VPS updated OR Navi task emitted
- [ ] Handoff appended

## Landmines to avoid
- **Don't commit `.env`**: both are gitignored. Verify.
- **Don't create a new GCP project**: work inside 585154028800.
- **Don't pick "Web application" again**: Desktop app only.
- **Don't remove `prompt=consent`**: without it Google re-issues the stale token.
- **Don't change `GOOGLE_ADS_DEVELOPER_TOKEN` or `GOOGLE_ADS_CUSTOMER_ID`**: only the three OAuth-related keys.
- **Don't try the Web client's redirect URI hack**: adding `http://localhost:<fixed-port>` to the existing Web client's URIs works in theory but Google has been rejecting new `http://localhost` entries on Web clients for over a year. Desktop client is the only clean path.

## If you get stuck
Don't defer again. The only legitimate blockers are:
- GCP project access is revoked → report that explicitly
- Google Ads API returns a real authorization error on step 6 (e.g., account was suspended) → report that explicitly

Anything else — grind through it.
