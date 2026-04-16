# Session Handoff — 2026-04-16 (Office / Google Ads Prep)

## Status entering this session
Pricing across the site is accurate and in-sync as of end-of-day 2026-04-15. Sale rotation refreshed. Store is ready for ads prep.

## Tomorrow's priority: Pre-flight before Google Ads campaign

$700 Google Ads credit expires **2026-05-31**. Do NOT launch ads until items 1 + 2 are done — without them, spend burns with no learning back.

### 1. Conversion tracking (HARD GATE)
- Install Google Ads tag on Shopify checkout
- Fire a `purchase` conversion event on order-complete
- Options:
  - Shopify's built-in Google & YouTube app supports conversion tracking — check if already enabled under app settings (Customer ID 822-210-2291 is already linked)
  - Otherwise: Shopify Admin → Online Store → Custom Pixels, add a Google Ads pixel similar to the Google Customer Reviews pixel (ID 149717026, already live)
- Verify in Google Ads → Tools → Conversions → Tag Assistant

### 2. End-to-end test purchase
- Place a real (or $0.50) order as a customer
- Confirm:
  - Checkout works, payment clears (Shopify Payments)
  - Order confirmation email sends
  - Order appears in Shopify admin + dashboard
  - **Google Ads conversion fires** (Tag Assistant live debug)
  - Google Customer Reviews opt-in email arrives
- If conversion doesn't fire → fix before ads, not after

### 3. Negative keyword seed list
Retro gaming queries frequently pull freeloaders and emulator hunters. Pre-load negatives:
```
rom, roms, rom download, rom pack
emulator, emulators, retroarch
free, cracked, pirate, piracy, torrent
iso, bios, cia file, nsp, xci
how to play, tutorial, review, retrospective, walkthrough
download, ebook, pdf
wikipedia, reddit, fandom
homebrew
```
Apply as campaign-level negative keyword list.

## After launch
- Start campaign conservatively (~$14/day to consume $700 over ~50 days)
- Focus first campaign on Shopping (Merchant Center has 12K+ approved products)
- Watch Search Terms report daily for week 1, add new negatives
- ROAS target: ≥ 3x to stay above transaction fees + COGS

## Lower-priority / later
- Homepage frontend revamp (banners, styling) — not a blocker for Shopping ads (which land on product pages)
- YouTube Shopping unlocks at 1,000 subs (podcast-dependent)
- Pokemon set imports me3 + me2pt5 when TCGPlayer pricing populates
- ~92 retro games with no PriceCharting data — hand-price or delist (low priority, long tail)

## Today's completed work (2026-04-15)
- PC-direct refresh: 1,303 variant prices fixed, 944 products processed (89.7% PC match)
- Manual fixes: Chrono Trigger, Mystical Ninja, Earthbound (DKO-ceiling cap applied)
- 3-way validator built (`scripts/validate-prices-3way.py`) — PC vs ours vs DKOldies
- Sale rotation swapped: 10 old games cleared, 8 iconic titles now 15% off (Mario 64, OoT, Super Mario World, SMB3, Crash Bandicoot 2, Sonic 2, Castlevania SOTN, Super Smash Bros)
- Console bundle sales untouched (N64/PS2/NES bundles remain on sale — intentional)
