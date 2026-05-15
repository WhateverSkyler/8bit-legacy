#!/usr/bin/env python3
"""Canonical applier — read a fresh search-refresh CSV and apply price corrections to Shopify.

Goal: every variant ends up at (market × multiplier × $X.99-rounded) OR is
quarantined to the review queue with a documented reason.

Replaces the patchwork of apply-pricing-fixes.py, apply-cross-console-fixes.py,
apply-wii-critical-fixes.py, fix-bad-prices.py. One canonical path.

Hard-fail conditions (exit non-zero before any write):
  - Circuit breaker `pricing` tripped
  - CSV file is older than --max-age-hours (default 24)
  - CSV is missing required columns

Per-row guardrails (skip and quarantine, do not apply):
  - Title contains 2+ console families (corruption from prior find-replaces)
  - PriceCharting "no match" or NaN market price
  - target/current ratio > MAX_NEW_OVER_OLD (likely matcher error)
  - current/target ratio > MAX_OLD_OVER_NEW (likely matcher error in the other direction)
  - new_price > MAX_PRICE (sanity cap)
  - new_price < $1 (too low to be real)
  - |variance| < MIN_DELTA_PCT (trivial change, not worth a Shopify write)

Apply behavior:
  - Re-fetch live Shopify price before each write (CSV may have drifted)
  - If live differs from CSV's old_price by >5%, recompute variance vs live
  - Shopify GraphQL productVariantsBulkUpdate, rate-limited at SHOPIFY_DELAY
  - Insert a price_snapshots row tagged source='truth_set_apply' for every write
  - Hard kill: 50 consecutive write failures → abort + re-trip the breaker

Usage:
  python3 scripts/apply-truth-set.py                  # dry-run preview
  python3 scripts/apply-truth-set.py --csv PATH       # specify CSV
  python3 scripts/apply-truth-set.py --apply          # actually write to Shopify
  python3 scripts/apply-truth-set.py --apply --skip-breaker-check  # override (dangerous)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT / "config" / ".env")
load_dotenv(PROJECT / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
DASHBOARD_DB = PROJECT / "dashboard" / "db" / "8bitlegacy.db"
LOG_DIR = PROJECT / "data" / "logs"

# Guardrails — tuned for "get to 100% accurate" cleanup pass.
MAX_NEW_OVER_OLD = 3.0       # Reject if target > 3x current (smoking-gun matcher error)
MAX_OLD_OVER_NEW = 3.0       # Reject if current > 3x target (other-direction matcher error)
MAX_PRICE = 800.0            # Absolute sanity cap (retro games)
MIN_NEW_PRICE = 1.00         # Below this is nonsense
MIN_DELTA_PCT = 1.0          # Skip if within 1% (rounding noise)
MIN_DOLLAR_DELTA = 0.50      # Skip cents-only changes
DOWN_QUARANTINE_PCT = 30.0   # Drops > this fraction go to review queue (could be matcher error)
SHOPIFY_DELAY = 0.3          # Rate-limit between Shopify mutations
CONSECUTIVE_FAIL_KILL = 50   # Abort + re-trip breaker after N consecutive failures

# Title-corruption sniffer — products like "Foo - NES Game - PS1 Game" mix two
# console families from prior find-replace accidents. Matcher results on these
# are unreliable; skip rather than apply a guess.
CONSOLE_TOKENS = ["nes", "snes", "n64", "nintendo 64", "gamecube", "wii", "wii u",
                  "gameboy", "gba", "gbc", "ds game", "3ds", "ps1", "ps2", "ps3",
                  "psp", "xbox", "genesis", "saturn", "dreamcast", "atari",
                  "master system", "playstation", "32x", "sega cd"]
CONSOLE_FAMILIES = {
    "nintendo": {"nes", "snes", "n64", "nintendo 64", "gamecube", "wii", "wii u",
                 "gameboy", "gba", "gbc", "ds game", "3ds"},
    "playstation": {"ps1", "ps2", "ps3", "psp", "playstation"},
    "sega": {"genesis", "saturn", "dreamcast", "master system", "32x", "sega cd"},
    "xbox": {"xbox"},
    "atari": {"atari"},
}


def title_is_corrupted(title: str) -> bool:
    lower = title.lower()
    hits = {tok for tok in CONSOLE_TOKENS if tok in lower}
    fam_hits = {fam for fam, toks in CONSOLE_FAMILIES.items() if hits & toks}
    return len(fam_hits) >= 2


# ── Circuit breaker check ─────────────────────────────────────────────

def breaker_tripped() -> tuple[bool, str]:
    """Returns (tripped, reason). Reads the dashboard's settings table."""
    if not DASHBOARD_DB.exists():
        return False, "no dashboard DB found"
    try:
        conn = sqlite3.connect(str(DASHBOARD_DB))
        row = conn.execute(
            "SELECT value FROM settings WHERE key='circuit_breaker_pricing'"
        ).fetchone()
        conn.close()
        if not row:
            return False, "no row in settings"
        state = json.loads(row[0])
        return bool(state.get("tripped")), state.get("reason", "")
    except Exception as e:
        return False, f"check error: {e}"


def trip_breaker(reason: str) -> None:
    """Trip the pricing breaker (used as kill-switch on consecutive failures)."""
    if not DASHBOARD_DB.exists():
        return
    now = datetime.now(timezone.utc).isoformat()
    state = json.dumps({"tripped": True, "reason": reason, "trippedAt": now})
    try:
        conn = sqlite3.connect(str(DASHBOARD_DB))
        conn.execute(
            "INSERT INTO settings(key,value,updated_at) VALUES('circuit_breaker_pricing',?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (state, now),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"WARN: failed to trip breaker: {e}")


# ── Shopify ───────────────────────────────────────────────────────────

def shopify_gql(query: str, variables: dict | None = None) -> dict:
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-04/graphql.json"
    r = requests.post(
        url,
        json={"query": query, "variables": variables or {}},
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def find_variant(product_title: str, variant_label: str) -> dict | None:
    """Lookup a Shopify variant by product title + variant label."""
    q = """query($q: String!) {
      products(first: 5, query: $q) {
        edges { node {
          id title
          variants(first: 10) { edges { node { id title price } } }
        } }
      }
    }"""
    res = shopify_gql(q, {"q": f'title:"{product_title.replace(chr(34), "")}"'})
    for edge in res.get("data", {}).get("products", {}).get("edges", []):
        node = edge["node"]
        if node["title"].lower().strip() != product_title.lower().strip():
            continue
        for v_edge in node["variants"]["edges"]:
            v = v_edge["node"]
            v_lower = v["title"].lower().strip()
            label_lower = variant_label.lower().strip()
            if v_lower == label_lower or label_lower in v_lower or v_lower in label_lower:
                return {
                    "variantId": v["id"], "productId": node["id"],
                    "currentPrice": float(v["price"]), "variantTitle": v["title"],
                }
    return None


def update_variant_price(product_id: str, variant_id: str, new_price: float) -> tuple[bool, str]:
    mut = """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants { id price }
        userErrors { field message }
      }
    }"""
    res = shopify_gql(mut, {
        "productId": product_id,
        "variants": [{"id": variant_id, "price": f"{new_price:.2f}"}],
    })
    errs = res.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
    if errs:
        return False, "; ".join(f"{e.get('field')}: {e.get('message')}" for e in errs)
    return True, ""


def snapshot_price(variant_id: str, old: float, new: float, market: float, source: str) -> None:
    if not DASHBOARD_DB.exists():
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn = sqlite3.connect(str(DASHBOARD_DB))
        conn.execute(
            "INSERT INTO price_snapshots(variant_id, old_price, new_price, market_price, source, captured_at) "
            "VALUES(?,?,?,?,?,?)",
            (variant_id, old, new, market, source, now),
        )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        # Schema may differ; degrade gracefully — the CSV log is authoritative
        pass
    except Exception:
        pass


# ── CSV handling ──────────────────────────────────────────────────────

REQUIRED_COLS = {"product", "console", "variant", "type", "market_price", "old_price", "new_price", "status"}


def parse_csv_row(row: dict) -> dict | None:
    """Coerce CSV row to typed dict, return None if invalid."""
    if row.get("status") == "NO_MATCH":
        return None
    try:
        market = float(row.get("market_price") or 0)
        old = float(row.get("old_price") or 0)
        new = float(row.get("new_price") or 0)
        if market <= 0 or new <= 0:
            return None
    except (ValueError, TypeError):
        return None
    return {
        "product": row["product"],
        "console": row["console"],
        "variant": row["variant"],
        "type": row["type"],
        "market": market,
        "old": old,
        "new": new,
    }


def classify(r: dict) -> tuple[str, str]:
    """Return (action, reason). action ∈ {APPLY, QUARANTINE_DOWN, QUARANTINE_ERR, SKIP_NOOP, SKIP_TITLE}."""
    if title_is_corrupted(r["product"]):
        return "SKIP_TITLE", "title has 2+ console families"
    new, old = r["new"], r["old"]
    if new > MAX_PRICE:
        return "QUARANTINE_ERR", f"new_price ${new:.2f} > sanity cap ${MAX_PRICE}"
    if new < MIN_NEW_PRICE:
        return "QUARANTINE_ERR", f"new_price ${new:.2f} below floor ${MIN_NEW_PRICE}"
    if old <= 0:
        return "QUARANTINE_ERR", "no current price"
    delta = new - old
    if abs(delta) < MIN_DOLLAR_DELTA:
        return "SKIP_NOOP", f"delta ${delta:.2f} below threshold"
    delta_pct = (new - old) / old * 100.0
    if abs(delta_pct) < MIN_DELTA_PCT:
        return "SKIP_NOOP", f"delta {delta_pct:.1f}% within rounding"
    # Matcher-error guards
    ratio_up = new / old if old > 0 else float("inf")
    ratio_down = old / new if new > 0 else float("inf")
    if ratio_up > MAX_NEW_OVER_OLD:
        return "QUARANTINE_ERR", f"target {ratio_up:.1f}x current (matcher-error suspect)"
    if ratio_down > MAX_OLD_OVER_NEW:
        return "QUARANTINE_ERR", f"current {ratio_down:.1f}x target (matcher-error suspect)"
    # Downward changes >30% go to review queue
    if delta_pct <= -DOWN_QUARANTINE_PCT:
        return "QUARANTINE_DOWN", f"price drop {delta_pct:.1f}% (review before applying)"
    return "APPLY", f"variance {delta_pct:+.1f}%"


# ── Main ──────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Apply truth-set price corrections to Shopify.")
    p.add_argument("--csv", default=None, help="Path to search-refresh CSV (default: latest in data/logs)")
    p.add_argument("--apply", action="store_true", help="Actually write to Shopify (default: dry-run)")
    p.add_argument("--max-age-hours", type=float, default=24.0, help="Reject CSV older than this")
    p.add_argument("--skip-breaker-check", action="store_true", help="DANGER: bypass circuit breaker")
    p.add_argument("--limit", type=int, default=None, help="Cap rows processed (debug)")
    args = p.parse_args()

    # Circuit breaker
    tripped, reason = breaker_tripped()
    if tripped and not args.skip_breaker_check:
        log(f"FATAL: pricing circuit breaker is tripped: {reason}")
        log("Pass --skip-breaker-check to override (only after verifying the matcher is safe).")
        return 3
    if tripped and args.skip_breaker_check and args.apply:
        log(f"WARNING: breaker is tripped but --skip-breaker-check is set. Proceeding.")

    # CSV
    if args.csv:
        csv_path = Path(args.csv)
    else:
        candidates = sorted(LOG_DIR.glob("search-refresh-*.csv"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            log("FATAL: no search-refresh CSV found in data/logs/")
            return 2
        csv_path = candidates[-1]
        log(f"Auto-selected CSV: {csv_path.name}")
    if not csv_path.exists():
        log(f"FATAL: CSV not found: {csv_path}")
        return 2
    age_hours = (time.time() - csv_path.stat().st_mtime) / 3600
    if age_hours > args.max_age_hours:
        log(f"FATAL: CSV is {age_hours:.1f}h old (>{args.max_age_hours}h). Re-run rescan first.")
        return 2

    # Env
    if args.apply and (not SHOPIFY_STORE or not SHOPIFY_TOKEN):
        log("FATAL: SHOPIFY_STORE_URL / SHOPIFY_ACCESS_TOKEN not set")
        return 4

    log(f"CSV age: {age_hours:.1f}h | mode: {'APPLY' if args.apply else 'DRY-RUN'}")

    # Parse + classify
    with open(csv_path) as f:
        rows_in = list(csv.DictReader(f))
    missing = REQUIRED_COLS - set(rows_in[0].keys() if rows_in else {})
    if missing:
        log(f"FATAL: CSV missing columns: {missing}")
        return 2

    log(f"Loaded {len(rows_in)} rows from {csv_path.name}")

    actions = {"APPLY": [], "QUARANTINE_DOWN": [], "QUARANTINE_ERR": [], "SKIP_NOOP": [], "SKIP_TITLE": [], "INVALID": []}
    for raw in rows_in:
        r = parse_csv_row(raw)
        if r is None:
            actions["INVALID"].append({"product": raw.get("product"), "reason": raw.get("status", "invalid")})
            continue
        action, reason = classify(r)
        actions[action].append({**r, "reason": reason})

    log("=" * 60)
    log("CLASSIFICATION SUMMARY")
    log("=" * 60)
    for k, v in actions.items():
        log(f"  {k:18s} : {len(v)}")

    if args.limit:
        actions["APPLY"] = actions["APPLY"][: args.limit]
        log(f"--limit applied: capped APPLY to {len(actions['APPLY'])} rows")

    # Write quarantine logs
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for bucket in ("QUARANTINE_DOWN", "QUARANTINE_ERR", "SKIP_TITLE"):
        if actions[bucket]:
            out = LOG_DIR / f"review-queue-{bucket.lower()}-{ts}.csv"
            with open(out, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["product", "console", "variant", "type", "market", "old", "new", "reason"])
                w.writeheader()
                w.writerows(actions[bucket])
            log(f"  → wrote {out.name}")

    if not args.apply:
        log("DRY-RUN — no Shopify mutations. Re-run with --apply to write.")
        # Sample preview
        log("\nSample APPLY candidates (first 10):")
        for r in actions["APPLY"][:10]:
            log(f"  {r['product']} [{r['variant']}] ${r['old']:.2f} → ${r['new']:.2f}  ({r['reason']})")
        return 0

    # APPLY
    log("=" * 60)
    log(f"APPLYING {len(actions['APPLY'])} changes to Shopify")
    log("=" * 60)

    out_csv = LOG_DIR / f"applied-truth-set-{ts}.csv"
    consecutive_fails = 0
    applied = 0
    failed = 0
    skipped_live = 0

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product", "console", "variant", "type", "market",
                                          "csv_old", "live_old", "new", "result", "error"])
        w.writeheader()
        for i, r in enumerate(actions["APPLY"], 1):
            # Re-fetch live price — CSV may be stale
            try:
                live = find_variant(r["product"], r["variant"])
            except Exception as e:
                failed += 1
                consecutive_fails += 1
                w.writerow({**r, "csv_old": r["old"], "live_old": "", "result": "LOOKUP_ERR", "error": str(e)})
                if consecutive_fails >= CONSECUTIVE_FAIL_KILL:
                    log(f"KILL: {CONSECUTIVE_FAIL_KILL} consecutive failures — tripping breaker")
                    trip_breaker(f"apply-truth-set: {CONSECUTIVE_FAIL_KILL} consecutive failures")
                    return 5
                time.sleep(SHOPIFY_DELAY)
                continue

            if live is None:
                failed += 1
                w.writerow({**r, "csv_old": r["old"], "live_old": "", "result": "NOT_FOUND", "error": "variant not on Shopify"})
                continue

            consecutive_fails = 0
            live_old = live["currentPrice"]

            # Re-classify against live price (CSV could have drifted)
            live_r = {**r, "old": live_old}
            live_action, live_reason = classify(live_r)
            if live_action != "APPLY":
                skipped_live += 1
                w.writerow({**r, "csv_old": r["old"], "live_old": live_old,
                            "result": f"SKIP_LIVE_{live_action}", "error": live_reason})
                continue

            ok, err = update_variant_price(live["productId"], live["variantId"], r["new"])
            if ok:
                applied += 1
                snapshot_price(live["variantId"], live_old, r["new"], r["market"], "truth_set_apply")
                w.writerow({**r, "csv_old": r["old"], "live_old": live_old,
                            "result": "APPLIED", "error": ""})
                if applied % 25 == 0:
                    log(f"  applied {applied}/{len(actions['APPLY'])}  (skipped-live={skipped_live}, failed={failed})")
            else:
                failed += 1
                consecutive_fails += 1
                w.writerow({**r, "csv_old": r["old"], "live_old": live_old,
                            "result": "FAILED", "error": err})
                if consecutive_fails >= CONSECUTIVE_FAIL_KILL:
                    log(f"KILL: {CONSECUTIVE_FAIL_KILL} consecutive failures — tripping breaker")
                    trip_breaker(f"apply-truth-set: {CONSECUTIVE_FAIL_KILL} consecutive failures")
                    return 5

            time.sleep(SHOPIFY_DELAY)

    log("=" * 60)
    log(f"DONE. applied={applied}  skipped_live={skipped_live}  failed={failed}")
    log(f"Output: {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
