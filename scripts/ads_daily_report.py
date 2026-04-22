#!/usr/bin/env python3
"""Daily performance report for the 8BL-Shopping-Games campaign.

Outputs a concise text report covering:
- Yesterday + last-7-day spend / clicks / impressions / conv / ROAS
- Circuit-breaker status (lifetime spend vs conversions)
- Top 20 new search terms (for negative-keyword consideration)
- Top 5 products by spend — flag any with 10+ clicks and 0 conversions
- Listing group performance (over_50 vs 20_to_50 tier)
- Any conversion action showing Inactive

Run manually or via cron. Designed for stdout; pipe to email / Slack / Navi task as needed.

Usage:
  python3 scripts/ads_daily_report.py                # Yesterday + last 7 days
  python3 scripts/ads_daily_report.py --since 2026-04-22   # since specific date
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

DEV_TOKEN = os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]
CLIENT_ID = os.environ["GOOGLE_ADS_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_ADS_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GOOGLE_ADS_REFRESH_TOKEN"]
CUSTOMER_ID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

API_VERSION = "v21"
BASE = f"https://googleads.googleapis.com/{API_VERSION}/customers/{CUSTOMER_ID}"

# Kill-switch thresholds (mirror dashboard/src/lib/safety.ts HARD_LIMITS)
DAILY_SPEND_CAP = 40.00
LIFETIME_NO_CONV_CEILING = 50.00


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


def search(query: str, token: str) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": DEV_TOKEN,
        "Content-Type": "application/json",
    }
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID
    r = requests.post(
        f"{BASE}/googleAds:searchStream",
        headers=headers,
        json={"query": query},
        timeout=60,
    )
    if r.status_code >= 400:
        print(f"API error {r.status_code}: {r.text[:400]}", file=sys.stderr)
        return []
    data = r.json()
    out = []
    for chunk in data if isinstance(data, list) else [data]:
        out.extend(chunk.get("results", []))
    return out


def dollars(micros: int | str | None) -> float:
    if not micros:
        return 0.0
    return int(micros) / 1_000_000


def fmt_money(n: float) -> str:
    return f"${n:,.2f}"


def header(s: str) -> None:
    print()
    print(s)
    print("─" * len(s))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD — instead of last 7 days")
    args = ap.parse_args()

    tok = get_token()
    today = date.today()
    yesterday = today - timedelta(days=1)
    since = args.since or (today - timedelta(days=7)).isoformat()

    print(f"8-Bit Legacy — Google Ads Daily Report")
    print(f"Date: {today.isoformat()}  |  Yesterday: {yesterday.isoformat()}  |  Trailing window from: {since}")

    # ── Campaign summary
    header("Campaign (current state)")
    rows = search(
        "SELECT campaign.id, campaign.name, campaign.status, campaign_budget.amount_micros "
        "FROM campaign WHERE campaign.name = '8BL-Shopping-Games'",
        tok,
    )
    if not rows:
        print("  NO CAMPAIGN FOUND.")
        return 1
    c = rows[0]["campaign"]
    b = rows[0]["campaignBudget"]
    print(f"  {c['name']}  status={c['status']}  budget={fmt_money(dollars(b['amountMicros']))}/day")

    # ── Yesterday performance (attributed to the campaign)
    header(f"Yesterday ({yesterday.isoformat()})")
    rows = search(
        f"SELECT metrics.cost_micros, metrics.clicks, metrics.impressions, "
        f"metrics.ctr, metrics.conversions, metrics.conversions_value, metrics.average_cpc "
        f"FROM campaign WHERE campaign.name = '8BL-Shopping-Games' AND segments.date = '{yesterday.isoformat()}'",
        tok,
    )
    if rows:
        m = rows[0]["metrics"]
        spend = dollars(m.get("costMicros", 0))
        clicks = m.get("clicks", 0)
        impr = m.get("impressions", 0)
        ctr = float(m.get("ctr", 0)) * 100 if m.get("ctr") else 0
        conv = float(m.get("conversions", 0))
        conv_val = float(m.get("conversionsValue", 0))
        avg_cpc = dollars(m.get("averageCpc", 0))
        roas = (conv_val / spend * 100) if spend > 0 else 0
        print(f"  spend={fmt_money(spend)}  clicks={clicks}  impr={impr}  "
              f"CTR={ctr:.2f}%  avg_cpc={fmt_money(avg_cpc)}")
        print(f"  conv={conv}  conv_value={fmt_money(conv_val)}  ROAS={roas:.0f}%")
        if spend >= DAILY_SPEND_CAP:
            print(f"  ⚠ spend hit daily hard cap of {fmt_money(DAILY_SPEND_CAP)}")
    else:
        print("  no data for yesterday (campaign probably paused)")

    # ── Trailing window
    header(f"Trailing since {since}")
    rows = search(
        f"SELECT metrics.cost_micros, metrics.clicks, metrics.impressions, "
        f"metrics.ctr, metrics.conversions, metrics.conversions_value "
        f"FROM campaign WHERE campaign.name = '8BL-Shopping-Games' AND segments.date >= '{since}'",
        tok,
    )
    total_spend = total_clicks = total_impr = 0
    total_conv = total_conv_val = 0.0
    for row in rows:
        m = row["metrics"]
        total_spend += dollars(m.get("costMicros", 0))
        total_clicks += m.get("clicks", 0)
        total_impr += m.get("impressions", 0)
        total_conv += float(m.get("conversions", 0))
        total_conv_val += float(m.get("conversionsValue", 0))
    ctr = (total_clicks / total_impr * 100) if total_impr > 0 else 0
    cvr = (total_conv / total_clicks * 100) if total_clicks > 0 else 0
    cpa = (total_spend / total_conv) if total_conv > 0 else 0
    roas = (total_conv_val / total_spend * 100) if total_spend > 0 else 0
    print(f"  spend={fmt_money(total_spend)}  clicks={total_clicks}  impr={total_impr}  CTR={ctr:.2f}%")
    print(f"  conv={total_conv}  CPA={fmt_money(cpa)}  conv_value={fmt_money(total_conv_val)}  ROAS={roas:.0f}%  CVR={cvr:.2f}%")

    # ── Kill-switch status
    header("Kill-switch status")
    # Google Ads API requires a finite date range on metrics queries — use "since 2 years ago" as effective lifetime
    two_years_ago = (today - timedelta(days=730)).isoformat()
    all_time = search(
        f"SELECT metrics.cost_micros, metrics.conversions "
        f"FROM campaign WHERE campaign.name = '8BL-Shopping-Games' AND segments.date >= '{two_years_ago}'",
        tok,
    )
    lifetime_spend = sum(dollars(r["metrics"].get("costMicros", 0)) for r in all_time)
    lifetime_conv = sum(float(r["metrics"].get("conversions", 0)) for r in all_time)
    if lifetime_spend >= LIFETIME_NO_CONV_CEILING and lifetime_conv == 0:
        print(f"  🔴 CEILING HIT: {fmt_money(lifetime_spend)} cumulative with 0 conversions "
              f"(hard pause at {fmt_money(LIFETIME_NO_CONV_CEILING)})")
    else:
        pct = (lifetime_spend / LIFETIME_NO_CONV_CEILING * 100) if LIFETIME_NO_CONV_CEILING > 0 else 0
        print(f"  lifetime: {fmt_money(lifetime_spend)} spent, {lifetime_conv} conversions "
              f"({pct:.0f}% of {fmt_money(LIFETIME_NO_CONV_CEILING)} no-conv ceiling)")

    # ── Top search terms (for negative keyword review)
    header(f"Top search terms (last 7d by impressions)")
    rows = search(
        f"SELECT search_term_view.search_term, metrics.impressions, metrics.clicks, "
        f"metrics.cost_micros, metrics.conversions "
        f"FROM search_term_view WHERE campaign.name = '8BL-Shopping-Games' "
        f"AND segments.date DURING LAST_7_DAYS "
        f"ORDER BY metrics.impressions DESC LIMIT 20",
        tok,
    )
    if rows:
        print(f"  {'impr':>6} {'clicks':>6} {'spend':>8} {'conv':>5}  term")
        for row in rows:
            t = row["searchTermView"]["searchTerm"]
            m = row["metrics"]
            print(f"  {m.get('impressions',0):>6} {m.get('clicks',0):>6} "
                  f"{fmt_money(dollars(m.get('costMicros',0))):>8} {float(m.get('conversions',0)):>5}  {t}")
    else:
        print("  no search terms yet (campaign paused or no data)")

    # ── Worst products (by spend with zero conversions)
    header(f"Product offenders (7d spend, 0 conv, ≥10 clicks)")
    rows = search(
        "SELECT segments.product_item_id, metrics.cost_micros, metrics.clicks, metrics.conversions "
        "FROM shopping_performance_view "
        "WHERE campaign.name = '8BL-Shopping-Games' AND segments.date DURING LAST_7_DAYS "
        "ORDER BY metrics.cost_micros DESC LIMIT 100",
        tok,
    )
    offenders = [r for r in rows
                 if r["metrics"].get("clicks", 0) >= 10 and float(r["metrics"].get("conversions", 0)) == 0]
    if offenders:
        for r in offenders[:10]:
            s = r.get("segments", {})
            m = r["metrics"]
            print(f"  spend={fmt_money(dollars(m.get('costMicros',0)))}  clicks={m.get('clicks')}  "
                  f"item_id={s.get('productItemId','?')}")
    else:
        print("  none (no offenders yet OR insufficient data)")

    # ── Conversion action health
    header("Conversion action health")
    rows = search(
        "SELECT conversion_action.name, conversion_action.status, conversion_action.primary_for_goal, "
        "metrics.all_conversions "
        "FROM conversion_action WHERE conversion_action.name LIKE 'Google Shopping App%' "
        "AND segments.date DURING LAST_30_DAYS",
        tok,
    )
    for row in rows:
        ca = row["conversionAction"]
        m = row.get("metrics", {})
        mark = "★" if ca.get("primaryForGoal") else " "
        print(f"  {mark} {ca['status']:10} {ca['name']:45}  30d_conv={m.get('allConversions', 0)}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
