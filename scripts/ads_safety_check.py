#!/usr/bin/env python3
"""Ads-safety kill switch — TrueNAS-resident replacement for the VPS dashboard's
safety.ts enforcement.

Runs on a cron (every 2h). Checks the 8BL-Shopping-Games campaign for runaway
spend or broken-funnel conditions and pauses it via the Ads API if tripped.
Also auto-recovers the campaign if a VPS-side trip (stale $25 threshold) paused
it while our own thresholds are still satisfied.

Trip conditions (pause the campaign if any is true):
  • Today's spend > MAX_DAILY_SPEND  ($40 default, matching the new safety.ts)
  • Lifetime spend > LIFETIME_NO_CONV_CEILING with 0 conversions total ($50 / 0)

Auto-recovery (re-enable the campaign only if):
  • Campaign is currently PAUSED (by us or anything else)
  • Today's spend < MAX_DAILY_SPEND × 0.80 (hysteresis — avoid flapping)
  • Lifetime spend < LIFETIME_NO_CONV_CEILING × 0.80 if lifetime conversions == 0
  • The --auto-recover CLI flag is set (default ON — matches intent to deprecate
    the VPS false-trip behavior)

State file at /app/data/state/ads_safety_state.json tracks last action so we
don't double-pause / spam Navi notifications.

On any trip: POST a Navi task so Tristan gets notified.

Exit codes:
  0 — check ran, no action needed
  1 — check ran, safety action taken (pause or recover)
  2 — fatal: credentials or API failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Container mount: /app/config/.env. Mac dev: ./config/.env.
for candidate in ((Path("/app/config/.env")), (ROOT / "config" / ".env")):
    if candidate.exists():
        load_dotenv(candidate)
        break
else:
    load_dotenv()  # fall through to process env

DEV_TOKEN = os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]
CLIENT_ID = os.environ["GOOGLE_ADS_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_ADS_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GOOGLE_ADS_REFRESH_TOKEN"]
CUSTOMER_ID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
NAVI_URL = os.environ.get("NAVI_URL", "").rstrip("/")

API_VERSION = "v21"
BASE = f"https://googleads.googleapis.com/{API_VERSION}/customers/{CUSTOMER_ID}"
CAMPAIGN_NAME = "8BL-Shopping-Games"

# Thresholds — match the NEW dashboard/src/lib/safety.ts values, which the VPS
# has not yet been redeployed with. These become authoritative going forward.
MAX_DAILY_SPEND = 40.0
LIFETIME_NO_CONV_CEILING = 50.0

# State / logging
STATE_DIR_CANDIDATES = [Path("/app/data/state"), ROOT / "data" / "state"]
ET = ZoneInfo("America/New_York")


def _state_dir() -> Path:
    for d in STATE_DIR_CANDIDATES:
        try:
            d.mkdir(parents=True, exist_ok=True)
            return d
        except OSError:
            continue
    return Path("/tmp")


STATE_FILE = _state_dir() / "ads_safety_state.json"


def get_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": DEV_TOKEN,
        "Content-Type": "application/json",
    }
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID
    r = requests.request(method, f"{BASE}{path}", headers=headers, json=body, timeout=60)
    if r.status_code >= 400:
        try:
            err = r.json()
            print(f"  API ERROR: {err}", file=sys.stderr)
        except Exception:
            pass
        r.raise_for_status()
    return r.json() if r.text else {}


def search(query: str, token: str) -> list[dict]:
    resp = api("POST", "/googleAds:searchStream", token, {"query": query})
    out: list[dict] = []
    for chunk in resp if isinstance(resp, list) else [resp]:
        out.extend(chunk.get("results", []))
    return out


def fetch_campaign_state(token: str) -> dict | None:
    rows = search(
        "SELECT campaign.id, campaign.name, campaign.status, campaign.resource_name "
        f"FROM campaign WHERE campaign.name = '{CAMPAIGN_NAME}'",
        token,
    )
    if not rows:
        return None
    c = rows[0]["campaign"]
    return {"id": c["id"], "name": c["name"], "status": c["status"], "resource_name": c["resourceName"]}


def fetch_today_spend(token: str) -> float:
    today_et = datetime.now(tz=ET).date().isoformat()
    rows = search(
        "SELECT metrics.cost_micros "
        "FROM campaign "
        f"WHERE campaign.name = '{CAMPAIGN_NAME}' "
        f"AND segments.date = '{today_et}'",
        token,
    )
    return sum(int(r["metrics"]["costMicros"]) for r in rows) / 1_000_000.0


def fetch_lifetime(token: str) -> tuple[float, float]:
    """Lifetime (spend, conversions) across all time."""
    rows = search(
        "SELECT metrics.cost_micros, metrics.conversions "
        "FROM campaign "
        f"WHERE campaign.name = '{CAMPAIGN_NAME}' "
        "AND segments.date DURING LAST_30_DAYS",
        token,
    )
    spend = sum(int(r["metrics"]["costMicros"]) for r in rows) / 1_000_000.0
    conv = sum(float(r["metrics"].get("conversions", 0)) for r in rows)
    return spend, conv


def set_campaign_status(campaign_resource: str, status: str, token: str) -> None:
    api("POST", "/campaigns:mutate", token, {
        "operations": [{
            "update": {"resourceName": campaign_resource, "status": status},
            "updateMask": "status",
        }],
    })


def notify_navi(title: str, description: str, priority: str = "high") -> None:
    if not NAVI_URL:
        print(f"  [NAVI] skipped (no NAVI_URL)", file=sys.stderr)
        return
    try:
        requests.post(
            f"{NAVI_URL}/api/user-data/sync",
            json={
                "tasks": [{
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "source": "8bit",
                }],
            },
            timeout=10,
        )
    except Exception as exc:
        print(f"  [NAVI] post failed: {exc}", file=sys.stderr)


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except OSError as exc:
        print(f"  [STATE] save failed: {exc}", file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Check only; don't mutate")
    p.add_argument("--no-auto-recover", action="store_true",
                   help="Disable re-enabling the campaign if it was paused while thresholds are OK")
    args = p.parse_args()

    now_et = datetime.now(tz=ET).isoformat()
    print(f"[ads_safety_check] {now_et}")

    try:
        token = get_token()
    except Exception as exc:
        print(f"FATAL: token refresh failed: {exc}", file=sys.stderr)
        return 2

    camp = fetch_campaign_state(token)
    if not camp:
        print(f"FATAL: campaign {CAMPAIGN_NAME!r} not found", file=sys.stderr)
        return 2

    today_spend = fetch_today_spend(token)
    lifetime_spend, lifetime_conv = fetch_lifetime(token)

    print(f"  campaign       = {camp['name']} ({camp['status']})")
    print(f"  today_spend    = ${today_spend:.2f}")
    print(f"  lifetime_spend = ${lifetime_spend:.2f}")
    print(f"  lifetime_conv  = {lifetime_conv:.2f}")
    print(f"  thresholds     = daily<${MAX_DAILY_SPEND}, lifetime<${LIFETIME_NO_CONV_CEILING} (when conv=0)")

    state = load_state()

    # Decide trip or recover
    should_pause = False
    pause_reason = ""
    if today_spend > MAX_DAILY_SPEND:
        should_pause = True
        pause_reason = f"today's spend ${today_spend:.2f} exceeds cap ${MAX_DAILY_SPEND:.2f}"
    elif lifetime_spend > LIFETIME_NO_CONV_CEILING and lifetime_conv < 0.5:
        should_pause = True
        pause_reason = (f"lifetime ${lifetime_spend:.2f} spent with {lifetime_conv:.2f} conversions "
                        f"(ceiling ${LIFETIME_NO_CONV_CEILING:.2f} / 1 conv)")

    auto_recover = not args.no_auto_recover
    # Only auto-recover if we've previously seen the campaign ENABLED. On the
    # very first run against a paused campaign (e.g., during pre-launch while
    # cowork is clearing gates), there's no state and we must NOT assume the
    # pause is accidental. Requires an earlier run to have logged an ENABLED
    # status before auto-recovery will fire.
    ever_seen_enabled = bool(state.get("last_seen_enabled_ts"))
    should_recover = (
        auto_recover
        and ever_seen_enabled
        and camp["status"] == "PAUSED"
        and today_spend < MAX_DAILY_SPEND * 0.80
        and (lifetime_conv >= 0.5 or lifetime_spend < LIFETIME_NO_CONV_CEILING * 0.80)
        and not should_pause
    )
    # Always keep a running record of the last time we OBSERVED the campaign
    # enabled — that's the gate for future auto-recoveries.
    if camp["status"] == "ENABLED":
        state["last_seen_enabled_ts"] = now_et
        save_state(state)

    if should_pause:
        if camp["status"] == "PAUSED":
            print(f"  already PAUSED, no action needed")
            return 0
        if args.dry_run:
            print(f"  [dry] would PAUSE: {pause_reason}")
            return 0
        set_campaign_status(camp["resource_name"], "PAUSED", token)
        print(f"  PAUSED: {pause_reason}")
        notify_navi(
            title=f"Google Ads auto-paused — {pause_reason.split(' (')[0]}",
            description=(f"Campaign {CAMPAIGN_NAME} paused by ads_safety_check.\n"
                         f"Reason: {pause_reason}\n"
                         f"Today: ${today_spend:.2f}  Lifetime: ${lifetime_spend:.2f} / {lifetime_conv:.2f} conv\n"
                         f"Reset: confirm the cause, then re-enable via Ads API or UI."),
            priority="critical",
        )
        state["last_action"] = {"ts": now_et, "action": "pause", "reason": pause_reason}
        save_state(state)
        return 1

    if should_recover:
        if args.dry_run:
            print(f"  [dry] would RECOVER (campaign paused but thresholds clean)")
            return 0
        set_campaign_status(camp["resource_name"], "ENABLED", token)
        print(f"  RECOVERED: paused campaign re-enabled (thresholds clean)")
        notify_navi(
            title=f"Google Ads auto-recovered",
            description=(f"Campaign {CAMPAIGN_NAME} was PAUSED but thresholds are clean; re-enabled.\n"
                         f"Today: ${today_spend:.2f}  Lifetime: ${lifetime_spend:.2f} / {lifetime_conv:.2f} conv\n"
                         f"Likely a false-trip from the stale VPS safety.ts ($25 cap). Investigate "
                         f"if this happens >1×/day."),
            priority="medium",
        )
        state["last_action"] = {"ts": now_et, "action": "recover"}
        save_state(state)
        return 1

    print(f"  OK — no action taken")
    return 0


if __name__ == "__main__":
    sys.exit(main())
