#!/usr/bin/env python3
"""
8-Bit Legacy — Test the orders/paid webhook handler

Replays a sample Shopify orders/paid payload against the dashboard's webhook
endpoint with a valid HMAC signature. Use this to verify the webhook is wired
up correctly without needing a real test purchase.

Usage:
  # Local dashboard
  python3 scripts/test_orders_paid_webhook.py --url http://localhost:3001/api/webhooks/shopify/orders-paid

  # Production VPS (needs nginx /api/webhooks/ bypass — see plan B6)
  python3 scripts/test_orders_paid_webhook.py --url https://8bit.tristanaddi.com/api/webhooks/shopify/orders-paid

  # With a custom gclid
  python3 scripts/test_orders_paid_webhook.py --gclid Cj0KCQjwTEST123abc

  # Without gclid — exercises the Enhanced Conversions path
  python3 scripts/test_orders_paid_webhook.py --no-gclid

  # Replay the SAME order ID twice — second call should short-circuit (dedup test)
  python3 scripts/test_orders_paid_webhook.py --order-id 9999999999
  python3 scripts/test_orders_paid_webhook.py --order-id 9999999999
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


def make_payload(order_id: str, gclid: str | None) -> dict:
    note_attributes = []
    if gclid:
        note_attributes.append({"name": "_gclid", "value": gclid})
        note_attributes.append({"name": "_gclid_captured_at", "value": "2026-05-01T12:00:00.000Z"})

    return {
        "id": int(order_id),
        "name": f"#TEST{order_id[-4:]}",
        "email": "tristanaddi1@gmail.com",
        "phone": "+12295551234",
        "currency": "USD",
        "total_price": "0.54",
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S-04:00"),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S-04:00"),
        "customer": {
            "email": "tristanaddi1@gmail.com",
            "phone": "+12295551234",
        },
        "note_attributes": note_attributes,
        "line_items": [
            {
                "title": "Black - Xbox Game (Game Only)",
                "quantity": 18,
                "price": "2.99",
                "sku": "TEST-SKU",
            }
        ],
    }


def sign(body: bytes, secret: str) -> str:
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")


def post(url: str, payload: dict, secret: str, valid_hmac: bool = True) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = sign(body, secret if valid_hmac else "wrong-secret")

    print(f"→ POST {url}")
    print(f"  order_id        = {payload['id']}")
    print(f"  total_price     = {payload['total_price']} {payload['currency']}")
    gclid_attr = next(
        (a["value"] for a in payload.get("note_attributes", []) if a.get("name") == "_gclid"),
        None,
    )
    print(f"  gclid           = {gclid_attr or '(none — Enhanced Conversions path)'}")
    print(f"  hmac (truncated)= {sig[:12]}...")

    resp = requests.post(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": sig,
            "X-Shopify-Topic": "orders/paid",
            "X-Shopify-Shop-Domain": "dpxzef-st.myshopify.com",
        },
        timeout=15,
    )
    print(f"← {resp.status_code} {resp.reason}")
    if resp.text:
        print(f"  body: {resp.text[:500]}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--url",
        default="http://localhost:3001/api/webhooks/shopify/orders-paid",
        help="Webhook endpoint URL",
    )
    p.add_argument("--secret", default=WEBHOOK_SECRET, help="HMAC secret (defaults to SHOPIFY_WEBHOOK_SECRET)")
    p.add_argument("--order-id", default=str(int(time.time())), help="Order ID to use (default: current epoch)")
    p.add_argument("--gclid", default=f"e2e_test_{int(time.time())}", help="gclid value to embed")
    p.add_argument("--no-gclid", action="store_true", help="Omit gclid (test Enhanced Conversions path)")
    p.add_argument("--bad-hmac", action="store_true", help="Send wrong HMAC signature (expect 401)")
    args = p.parse_args()

    if not args.secret:
        sys.exit("SHOPIFY_WEBHOOK_SECRET not set in env or --secret flag")

    payload = make_payload(args.order_id, None if args.no_gclid else args.gclid)
    post(args.url, payload, args.secret, valid_hmac=not args.bad_hmac)


if __name__ == "__main__":
    main()
