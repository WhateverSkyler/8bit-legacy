#!/usr/bin/env python3
"""
Discovery script: locate the Get In Touch sidebar in the theme.

Uses the Shopify Admin REST API to find files containing placeholder strings
from the sidebar (support@demo.com, 139 Brook Drive, etc.) so we know which
.liquid / .json files to edit to remove the sidebar.

Usage:
    python3 scripts/find-contact-sidebar.py

Output:
    - Lists current theme + all contact-related asset keys
    - For each file containing sidebar placeholders, prints filename and saves
      a local snapshot to data/theme-snapshot/<key>.
    - Prints line ranges of the matches so we know the rough block to remove.

This is read-only. It does NOT modify the theme.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "config" / ".env"
SNAPSHOT_DIR = ROOT / "data" / "theme-snapshot"

PLACEHOLDERS = [
    "support@demo.com",
    "139 Brook",
    "1067 USA",
    "Parking is only available",
    "0123456789",
    "Have An Question",
    "Openning Time",
    "Get In Touch",
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        sys.exit(f"Missing env file: {path}")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env(ENV_FILE)
SHOP = ENV["SHOPIFY_STORE_URL"].replace("https://", "").replace("http://", "").strip("/")
TOKEN = ENV["SHOPIFY_ACCESS_TOKEN"]
API_VERSION = ENV.get("SHOPIFY_API_VERSION", "2024-04")


def api(path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    url = f"https://{SHOP}/admin/api/{API_VERSION}/{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("X-Shopify-Access-Token", TOKEN)
    req.add_header("Accept", "application/json")
    data: bytes | None = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        sys.exit(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:500]}")


def find_lines(text: str, needle: str) -> list[int]:
    return [i + 1 for i, line in enumerate(text.splitlines()) if needle in line]


def main() -> int:
    themes = api("themes.json")["themes"]
    current = next((t for t in themes if t["role"] == "main"), None)
    if not current:
        sys.exit("No published (main) theme found.")
    theme_id = current["id"]
    print(f"Published theme: {current['name']!r} (id {theme_id})")

    assets = api(f"themes/{theme_id}/assets.json")["assets"]
    print(f"Total assets in theme: {len(assets)}")

    contact_keys = sorted(a["key"] for a in assets if "contact" in a["key"].lower())
    print(f"\nAssets with 'contact' in their key ({len(contact_keys)}):")
    for k in contact_keys:
        print(f"  {k}")

    # Scan only liquid + json (skip css/js/images/etc)
    scanable = [a for a in assets if a["key"].endswith((".liquid", ".json"))]
    print(f"\nScanning {len(scanable)} liquid/json assets for sidebar placeholders...")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    hits: dict[str, dict] = {}

    for a in scanable:
        key = a["key"]
        # fetch full content
        params = urllib.parse.urlencode({"asset[key]": key})
        full = api(f"themes/{theme_id}/assets.json?{params}")
        value = full.get("asset", {}).get("value", "")
        if not isinstance(value, str):
            continue
        found = {p: find_lines(value, p) for p in PLACEHOLDERS if p in value}
        if found:
            hits[key] = {"matches": found, "value": value}
            local = SNAPSHOT_DIR / key
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(value)

    if not hits:
        print("\nNo placeholder strings found in any liquid/json asset.")
        print("The sidebar may be coming from a JS-rendered app block or an external source.")
        return 0

    print(f"\n=== Found placeholders in {len(hits)} file(s) ===\n")
    for key, info in hits.items():
        print(f"FILE: {key}")
        for needle, lines in info["matches"].items():
            print(f"  {needle!r}: lines {lines}")
        print(f"  Snapshot saved: {SNAPSHOT_DIR / key}")
        print()

    print("Done. Snapshots are in data/theme-snapshot/ for review.")
    print(f"Theme ID for the next script: {theme_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
