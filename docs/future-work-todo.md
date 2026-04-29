# Future Work — Parking Lot

Things Tristan wants to remember for later. Not shoot-day specific, not actively in flight. When picking up one of these, flesh out scope in a dedicated doc and reference it back here.

## High-leverage automation ideas

### Recurring Claude Code business audit
Set up a scheduled remote agent (cron-based) that runs an overall business audit of 8-Bit Legacy on a recurring cadence (weekly? bi-weekly?). Scope to flesh out:
- **Shopify review** — orders, fulfillment health, low-stock alerts on hot SKUs, customer review trends
- **Weekly sales rotation** — pick next sale segment from `project_sales_rotation.md`, draft the discount config, queue for manual approval
- **Price audit** — sample N products across each console family, verify prices still ≥1.30x current PriceCharting market price, flag mispriced outliers
- **Ad performance summary** — once campaign is running, tie to the existing `ads_daily_report` agent
- **Inventory cadence** — Pokemon set freshness (new sets to import), CIB variant sanity check, Merchant Center disapproval drift
- Output: single Navi task per audit run with a punch-list of items needing human attention

Use existing `RemoteTrigger` infrastructure (per the Claude Code Recurring agent that already runs the ads daily review at `trig_01VHYi2ibCvAP9z8H6qU2tcG`). Probably similar pattern.

Added: 2026-04-29

### Automated cowork order fulfillment
Investigate whether a Claude cowork agent can handle order fulfillment end-to-end:
- Watch Shopify for new paid orders
- For each order line, find cheapest matching eBay listing (existing `ebay-finder.py` logic)
- Place the eBay order with correct shipping address
- Update Shopify order with tracking number once eBay supplies it
- Mark order fulfilled

Big DTR (Down To Research) — gates:
- Can browser MCP reliably drive eBay's checkout (CAPTCHA risk)?
- Authentication: how to keep eBay session alive across many orders / many days
- Payment: prepaid eBay gift cards? Linked card? PayPal?
- Error handling: what if listing sold out between price check and purchase?
- Tax: sales tax handling on out-of-state purchases (per `project_ebay_resale_exemption.md` — known leak)
- Risk model: what's the worst case if cowork buys the wrong item?

Probably needs to be opt-in per order initially (cowork stages the eBay cart, you approve + click Pay). Full autonomy later if reliability is high.

Added: 2026-04-29

---

## Format

When picking one of these up:
1. Move into a dedicated `docs/<topic>-plan.md`
2. Replace the bullet here with `[Done — see <link>]` or `[Active — see <link>]`
3. If abandoned, leave the bullet but mark `[Abandoned: reason]`
