# Cowork Brief — 2026-05-01 — Flip App Pixels to "Always On"

## Goal

Flip the **Google & YouTube** app pixel's data-sharing setting from `Optimized` to `Always on` in Shopify Admin → Settings → Customer events. While there, do the same for the **Facebook & Instagram** and the third unidentified app pixel (apiClientId `4383523`). All three are currently throttled by Shopify's January 2026 default change, suppressing Google Ads conversion events.

This is **NOT** in the G&Y app's iframe. It's a native Shopify Admin page (`/settings/customer_events`), so the iframe blocking that broke the previous MC cowork doesn't apply here.

Time budget: ~10 minutes.

## Hard guardrails — read first

✗ Do NOT click "Disconnect" / "Remove" / "Delete pixel" anywhere
✗ Do NOT click "Reinstall" or "Reauthorize" if surfaced
✗ Do NOT modify any Custom pixel (specifically the "Google Customer Reviews" pixel ID 149717026 — it's working as intended, leave it alone)
✗ Do NOT modify privacy settings, cookie banner config, or consent banner
✗ Do NOT touch "Google & YouTube" the *Sales channel* — only the *App pixel* (different things)
✗ Do NOT edit the Permissions tab's other settings (CustomerData scopes etc.) — only the data-sharing toggle
✗ Do NOT log in for Tristan — surface login walls if hit, don't bypass

If a confirmation dialog says "Are you sure?" in any unexpected context — screenshot, click Cancel, surface back to Tristan.

## Phase 1 — Navigate (1 min)

URL: `https://admin.shopify.com/store/dpxzef-st/settings/customer_events`

Capture verbatim:
- The page title (should be "Customer events" or similar)
- The list of tabs visible at the top (should include something like "All pixels", "App pixels", "Custom pixels")
- The complete list of pixels visible on the default landing tab — name, type (App/Custom), status, and the value in the **Permissions** / **Data** / **Customer data** column (this is the one we need to change — could be labeled different things in different Shopify versions)

## Phase 2 — Open the Google & YouTube App pixel detail (1 min)

On whichever tab shows it, click the row labeled **"Google & YouTube"** (NOT "Google Customer Reviews" — that's a custom pixel, leave it alone). The full name might be "Google & YouTube — Google" or similar.

Capture verbatim from the detail page:
- The page heading (pixel name)
- All sections visible on the detail page — common ones: "Connection / Status", "Permissions", "Customer privacy", "Data sharing", "Customer data", "Subscribed events", "API client ID"
- Specifically — find the section that controls data-sharing mode. Common labels:
  - "Customer privacy" with options like `Customer-managed` / `Always on`
  - "Data sharing" with options like `Optimized` / `Always on`
  - "Permissions" with the same
- Capture the **current selected value** for that control (we expect `Optimized`)
- Note ANY toggles, dropdowns, or radio buttons in that section

## Phase 3 — Flip to "Always on" (2 min, the actual mutation)

Switch the data-sharing control from `Optimized` to `Always on`. This is the only mutation in this entire brief.

Then **find and click Save**. The Save button can be:
- A sticky banner at the top of the page that appeared after the toggle ("Unsaved changes — Save")
- A "Save" button at the top-right
- A "Save" button at the bottom of the page

Click it. Wait for a confirmation toast (typically "Saved" / "Settings updated" / "Pixel updated").

If NO Save banner appeared after toggling, the change may have auto-saved. Refresh the page (F5 or Cmd+R) and verify the value persists as `Always on` — if so, Phase 3 is complete.

If toggling does NOT change anything (e.g. the radio button doesn't move), screenshot the state and surface back. Could be a permissions issue or a Shopify bug.

Capture:
- Timestamp at click of Save
- Verbatim text of the confirmation toast
- After page refresh: the value in the data-sharing control (should now read `Always on`)

## Phase 4 — Repeat for Facebook & Instagram (2 min)

Back on the App pixels list, click into **Facebook & Instagram** (or "Meta" — whichever name appears). Repeat Phase 2 + Phase 3.

If the name is different and there's no Facebook/Meta pixel listed — skip and document.

## Phase 5 — Repeat for the third app pixel (2 min)

There's an unidentified third app pixel — apiClientId `4383523`. Its name in the list might be "TikTok", "Bing Ads", "Pinterest", or something else. Look for any **App pixel** other than Google & YouTube and Facebook & Instagram, click into it, capture the name, repeat Phase 2 + Phase 3.

If only those two app pixels exist, document and skip.

## Phase 6 — Verify (2 min)

After all three are saved as `Always on`:

1. Run this in a terminal (or just describe what's needed in the handoff if you can't run a terminal): `curl -s "https://8bitlegacy.com/" | grep -oE '"dataSharingState":"[^"]+"'`
2. Expected output: 3 lines, each showing `"dataSharingState":"always_on"` or `"dataSharingState":"unrestricted"` (Shopify uses `unrestricted` in the API as the value for "Always on")
3. If any line still shows `optimized`, that pixel's flip didn't save → revisit Phase 3 for that one

You don't have to run the curl — just note in the handoff what URL/command to verify.

## Handoff

Write `docs/cowork-session-2026-05-01-pixel-flip.md` with:

```markdown
# Cowork Session — 2026-05-01 — App Pixel Flip to Always On

## Outcome
- [ ] All 3 app pixels successfully flipped to Always on
- [ ] Partial: Google & YouTube only (___ remaining)
- [ ] Failed at Phase ___ — surfacing back to Tristan
- [ ] Different UI than expected — described below for Tristan

## Phase 1 — Customer events page
URL loaded: ___
Tabs visible: ___
Pixel list (verbatim): ___

## Phase 2 — Google & YouTube detail page
Page heading: ___
Data-sharing control label and section: ___
Current value before flip: ___

## Phase 3 — Flip and save
Action taken: <verbatim>
Save click timestamp: ___
Confirmation toast: <verbatim>
Value after page refresh: ___

## Phase 4 — Facebook & Instagram
Same template. If skipped, why: ___

## Phase 5 — Third app pixel (apiClientId 4383523)
Identified name: ___
Same template. If skipped, why: ___

## Phase 6 — Verification
[describe steps run]

## Anything weird (free-form)
<verbatim screenshots of unexpected dialogs / banners / errors>
```

Commit + Syncthing-propagate. **Do NOT git push** (Tristan handles that).

## Time budget

Phase 1: 1 min
Phase 2: 1 min
Phase 3: 2 min
Phase 4: 2 min
Phase 5: 2 min
Phase 6: 2 min
Total: ~10 min wall clock

If exceeding 20 minutes, surface progress to Tristan rather than burning more time.
