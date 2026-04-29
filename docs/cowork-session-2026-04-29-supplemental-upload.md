# Cowork Session — 2026-04-29 — Supplemental Feed Upload

**Session start:** ~2:00 PM ET (afternoon session, after morning MC fix session)
**Brief:** `docs/claude-cowork-brief-2026-04-29-supplemental-feed-upload.md`

## TL;DR — DO NOT RE-UPLOAD WITHOUT NEW MECHANISM

The supplemental feed upload **broke 13,254 products** by acting as a competing primary feed instead of a true supplemental. **Source has been deleted**, recovery in progress (0 → 4,287 products in ~10 min after delete; full restoration expected within 4 hours via Shopify G&Y app's natural sync).

**The Shopify G&Y app's "Add product source" wizard does not create supplementals — it creates primaries.** Two primaries with the same country+language+feed label combination cause the most-recent-update to overwrite missing fields, which is why the 3-column CSV nulled out title/image/price/etc. for matched products.

**Main session: do NOT re-upload via the same path.** Confirm a different mechanism (Shopify metafields, Content API, or a true supplemental UI flow) before retrying.

---

## Upload outcome

- **Match rate: 100%** (13,254 of 13,254 CSV rows matched existing offer IDs)
- **Total rows uploaded:** 13,254
- **New products added:** 2 (offer IDs in CSV not previously in Feed B — supplemental introduced them)
- **Rows with errors:** 0
- **Error types (if any):** None during validation
- **MC reported:** "Your products are updated" / "Attribute names: All recognized" / "Your product file: No issues found"
- **Decision path taken:** Initially looked like ✅ Success → spot-check exposed catastrophic side effect → escalated to user → DELETED supplemental per user authorization → recovery in progress

### Side effect that wasn't visible in match-rate metrics

The 13,254 "matched" products had their core fields (title, image_link, price, brand, etc.) **nulled out** because:
- The CSV only contained 3 columns: `id`, `custom_label_0`, `custom_label_2`
- MC treated the file as a primary feed (URL was `createPrimaryFeed`) sharing Feed B's country+language+feed label
- Most-recent-update wins per-field merge logic → fields not in the CSV were treated as cleared

**MC product detail page after upload showed:**
- "Title pending or missing"
- No image (just "Add images" button)
- No price visible in right card
- Status: **Limited** — "showing on Google but limited discoverability"
- Source: File (the supplemental, not Feed B)
- Custom labels populated correctly: `20_to_50, game` ✅

Verified on:
1. Final Fantasy VII - PS1 Game Complete (CIB) — `shopify_ZZ_7956663664674_43794595676194`
2. Crisis Core: Final Fantasy VII - PSP Game Complete (CIB) — `shopify_ZZ_7956637876258_43794621399074`

After the delete, Feed B (USD_88038604834) showed **0 products** in the data sources list. The supplemental had absorbed all 13,252 of Feed B's offer IDs.

---

## Spot-check (post-upload)

- Product checked: **Final Fantasy VII - PS1 Game Complete (CIB)** ($55.99)
- custom_label_0 visible: **YES** (`20_to_50` — note tag is product-level, likely based on Game Only variant price not CIB)
- custom_label_2 visible: **YES** (`game`)
- BUT title/image/price: missing (the side effect described above)

---

## CSV format note

MC's "Upload a file from your computer" only accepts `.txt` (tab-delimited), `.xml`, `.tsv` — **NOT `.csv`**. Converted via simple `tr ',' '\t' < .csv > .tsv`. New file at `data/merchant-center-custom-labels.tsv` (735 KB, 13,255 lines, identical content). Worth updating the generator script to emit TSV directly when we figure out the right re-upload mechanism.

Also: file_upload via Cowork extension was blocked ("Not allowed") — Tristan had to drag-and-drop manually.

---

## Cleanup actions taken

1. **Created supplemental** via Shopify Admin → Sales channels → Google & YouTube → ... wait, no. Created via MC → Data sources → Add product source → "Upload a file from your computer", with feed label set to `USD_88038604834` to match Feed B. Source ID: `10646039059`, Type: File (manual). 8:48 AM PDT timestamp on creation.

2. **Spot-check exposed the issue** — surfaced to Tristan with full evidence (FFVII PS1 + Crisis Core both broken, Feed B count dropped to 0, supplemental count 13,252 = absorbed Feed B's offer ID set).

3. **Tristan authorized deletion** with explicit guidance: Option 3 (delete + wait for Feed B re-sync). Reasoning: every minute the supplemental sat there, Free Listings showed broken products. Deletion is fully reversible — labels are trivially regeneratable from the script. Worst case from delete = revert to pre-upload state.

4. **Deleted supplemental** via Data sources → ⋮ → Delete source → Remove. Confirmation accepted: "merchant-center-custom-labels.tsv, including all products in the file, will be permanently deleted from Merchant Center."

---

## Recovery status (auto-recovery, no intervention needed)

After delete, the Shopify Google & YouTube app's natural sync started auto-pushing products back to Feed B without any forced trigger.

| Time after delete | Total | Approved | Limited | Not Approved | Under Review |
|---|---|---|---|---|---|
| t+0 (immediately) | 0 | — | — | — | — |
| t+~10 min (per G&Y Overview) | **4,287** | **2,624** | **0** | **1,660** | **3** |
| Expected at full recovery | ~13,252 | ~12,775+ | 0 | ~470 | ~17 |

**Recovery rate:** ~32% in 10 min. Linear extrapolation suggests full recovery in 30–60 min, but Shopify's G&Y app may push in batches with cooldowns — could take up to 4 hours. Either way, autonomous and no further action needed.

The Shopify G&Y app does not expose a "Sync now" / "Resubmit feed" button:
- Settings → Product sync modal: BLOCKED by Shopify safety guardrail ("To turn it off, you need to have products in Google Merchant Center"). Manually radio greyed out, Save disabled. Cannot toggle off→on.
- Overview page kebab (...): only has Manage app / Get support / Review app / Pin to navigation / Uninstall. No sync action.
- Feed B's data source page: only has Edit countries / Delete source. No fetch/refresh (it's a Merchant API push, not a fetch).
- Disconnect/reconnect was REJECTED as an option — that's the exact mechanism that created the 4/24 Feed A vs Feed B duplication. Repeating it would risk creating a Feed C and forcing us to redo the morning's entire cleanup.

So: natural recovery is the only path, and it's already happening.

---

## If mismatch path: actual offer ID samples seen in MC

Mismatch path was NOT triggered — match rate was 100%. The shopify_ZZ_ prefix in the CSV correctly matched Feed B's offer ID format. The problem wasn't ID mismatch; it was the supplemental-vs-primary classification.

---

## Anything weird

- **The brief author's mental model of how MC Next supplementals work was wrong.** The brief assumed MC Next's "Add product source" wizard with a matching country+language+feed label = supplemental. In practice, MC Next treats it as a second primary, and per-field merge logic uses most-recent-update. A 3-column file becomes destructive because missing fields get treated as cleared.
- **Match rate metrics are misleading.** "Total updated products: 13,254" sounds like a clean success but actually meant "13,254 products had their full data clobbered by 3 columns of update." There's no MC UI affordance to detect this kind of data loss before it happens.
- **MC's Latest update screen showed initial total of 10,000** which I thought was a hard cap — turned out to be in-progress validation count. After refresh: 13,254. Worth noting for future uploads — wait and refresh before drawing conclusions.
- **Feed B's data was preserved server-side** — when supplemental was deleted, products started re-appearing in Feed B without an explicit Shopify push. That suggests MC retained Feed B's contributions in some form even when supplemental was overwriting display. Or the Shopify G&Y app polls MC's count and immediately repopulated when count dropped to 0.

---

## Status for flip

- **MC supplemental:** ❌ Failed approach — supplemental DELETED, do NOT retry without different mechanism
- **Custom labels in MC:** Not present (rolled back with the supplemental delete)
- **Estimated recovery ETA:** Feed B back to ~13,252 within 30 min – 4 hours via Shopify G&Y natural sync. CIB exclusion preserved (it's metafield-driven from Shopify side, not affected by this episode).
- **Anything Tristan needs to know before flip command?**
  1. ❌ **DO NOT FLIP YET.** Wait for Feed B to fully recover — verify Total back to ~13,252 and pick a few popular products to confirm titles/images/prices are restored.
  2. ❌ **DO NOT re-upload the supplemental** via the same Shopify Admin → MC → Add product source path. It will recreate the same data-clobber. Main session must determine the correct mechanism first (candidates: Shopify `mm-google-shopping.custom_label_0/2` metafields parallel to CIB exclusion approach, Content API per-product attribute updates, or a true MC supplemental UI flow we haven't found).
  3. ⚠️ **0–4 hour window of degraded Free Listings** for ~9–13K products as recovery completes. Storefront, Shopify orders, paid Google Ads (paused, $0 spend) all unaffected.
  4. ✅ All morning gains are intact: Feed A is still deleted, Feed B is still canonical, CIB exclusion via metafield is still working (verified before the supplemental disaster), no shipping/return/account issues introduced.

---

## What I did NOT do

- Did NOT flip the campaign
- Did NOT modify any Shopify product, tag, metafield, theme, or storefront
- Did NOT touch billing
- Did NOT place test orders
- Did NOT regenerate the CSV — TSV conversion was a format-only change (`tr ',' '\t'`), no data regeneration
- Did NOT delete or modify Feed B
- Did NOT disconnect/reconnect any Google service (rejected by user — that mechanism caused the 4/24 duplication)
- Did NOT toggle the Product sync radio in Shopify (couldn't anyway — Shopify safety guardrail blocked it because Feed B was empty)

---

## What changed during this session

- **Created** MC product source: `merchant-center-custom-labels.tsv` (Source ID `10646039059`, type File manual, country US, language English, feed label USD_88038604834) — uploaded TSV (13,254 rows custom labels mapping)
- **Deleted** that same source ~5 min later after spot-check exposed data-clobber
- **Created** TSV file: `data/merchant-center-custom-labels.tsv` (alongside the existing CSV) — same content, tab-delimited
- **No other MC-side changes**

---

## Next steps for main session

1. Investigate correct custom-labels propagation mechanism. Three candidates ranked by likelihood/cleanliness:
   - **Best:** Shopify `mm-google-shopping.custom_label_0` / `custom_label_2` metafields on each product — parallel to how CIB exclusion's `excluded_destination` already works through the G&Y app. If the G&Y app honors these, it's a one-shot Shopify-side fix and bridges custom labels through the canonical Feed B push.
   - **Backup:** Google Content API for Shopping — programmatic per-product attribute updates. Bypasses MC UI entirely. More code but full control.
   - **Last resort:** A true supplemental data source UI flow we haven't found yet (separate from "Add product source"). Maybe accessible via direct URL or a different account-level setting. Would need MC docs investigation.

2. Once mechanism is verified safe in a sandbox / single-product test, propagate labels for all 13K+ products.

3. After labels are confirmed in a few products' detail pages, proceed with campaign flip per `docs/google-ads-launch-plan.md`.
