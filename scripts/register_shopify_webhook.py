#!/usr/bin/env python3
"""
8-Bit Legacy — Register Shopify orders/paid webhook

Subscribes the dashboard's webhook endpoint to Shopify orders/paid events.
This is the server-side conversion-upload backstop for Google Ads — see
docs/ads-launch-resumption-2026-04-30.md for context.

The shared HMAC secret used to sign webhook payloads is the Shopify Custom
App's API secret key. Set it in dashboard/.env.local as SHOPIFY_WEBHOOK_SECRET
before deploying the webhook route.

Usage:
  # Default — registers https://8bit.tristanaddi.com/api/webhooks/shopify/orders-paid
  python3 scripts/register_shopify_webhook.py

  # Custom callback URL (e.g. ngrok tunnel for local testing)
  python3 scripts/register_shopify_webhook.py --url https://abc.ngrok.io/api/webhooks/shopify/orders-paid

  # List currently-registered webhook subscriptions
  python3 scripts/register_shopify_webhook.py --list

  # Delete a subscription by ID
  python3 scripts/register_shopify_webhook.py --delete gid://shopify/WebhookSubscription/123
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = "2024-10"

DEFAULT_CALLBACK_URL = "https://8bit.tristanaddi.com/api/webhooks/shopify/orders-paid"


def graphql(query: str, variables: dict | None = None) -> dict:
    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        sys.exit("SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set")
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        sys.exit(f"GraphQL errors: {json.dumps(body['errors'], indent=2)}")
    return body["data"]


def list_subscriptions() -> None:
    data = graphql(
        """
        query {
          webhookSubscriptions(first: 50) {
            edges {
              node {
                id
                topic
                endpoint { __typename ... on WebhookHttpEndpoint { callbackUrl } }
                format
                createdAt
              }
            }
          }
        }
        """
    )
    edges = data["webhookSubscriptions"]["edges"]
    if not edges:
        print("No webhook subscriptions registered.")
        return
    for edge in edges:
        n = edge["node"]
        ep = n.get("endpoint") or {}
        url = ep.get("callbackUrl", "(non-http endpoint)")
        print(f"{n['id']}\t{n['topic']}\t{n['format']}\t{url}\t{n['createdAt']}")


def register(url: str) -> None:
    data = graphql(
        """
        mutation registerOrdersPaid($url: URL!) {
          webhookSubscriptionCreate(
            topic: ORDERS_PAID,
            webhookSubscription: {
              callbackUrl: $url,
              format: JSON
            }
          ) {
            webhookSubscription { id topic format }
            userErrors { field message }
          }
        }
        """,
        {"url": url},
    )
    res = data["webhookSubscriptionCreate"]
    errs = res.get("userErrors") or []
    if errs:
        # Distinguish "already exists" (idempotent re-run) from real failures
        for err in errs:
            msg = err.get("message", "")
            if "already" in msg.lower() and "taken" in msg.lower():
                print(f"Already registered for this URL — no action taken.")
                return
        sys.exit(f"webhookSubscriptionCreate failed:\n{json.dumps(errs, indent=2)}")
    sub = res["webhookSubscription"]
    print(f"Registered: {sub['id']}")
    print(f"Topic:      {sub['topic']}")
    print(f"Format:     {sub['format']}")
    print(f"Callback:   {url}")


def delete(subscription_id: str) -> None:
    data = graphql(
        """
        mutation deleteSub($id: ID!) {
          webhookSubscriptionDelete(id: $id) {
            deletedWebhookSubscriptionId
            userErrors { field message }
          }
        }
        """,
        {"id": subscription_id},
    )
    res = data["webhookSubscriptionDelete"]
    if res.get("userErrors"):
        sys.exit(f"Delete failed: {json.dumps(res['userErrors'], indent=2)}")
    print(f"Deleted: {res['deletedWebhookSubscriptionId']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default=DEFAULT_CALLBACK_URL, help="Webhook callback URL")
    p.add_argument("--list", action="store_true", help="List existing subscriptions")
    p.add_argument("--delete", metavar="ID", help="Delete a subscription by GID")
    args = p.parse_args()

    if args.list:
        list_subscriptions()
    elif args.delete:
        delete(args.delete)
    else:
        register(args.url)


if __name__ == "__main__":
    main()
