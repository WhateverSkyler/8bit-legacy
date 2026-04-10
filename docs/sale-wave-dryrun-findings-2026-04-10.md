# Sale Wave Dry-Run Findings — 2026-04-10

**Ran by:** Terminal Claude session
**Status:** Both layers have problems. Recommend NOT running `--apply` until they're addressed.

---

## Layer 1 — Under $20, 15% off

**Command:** `python3 scripts/manage-sales.py --max-price 20 --discount 15 --dry-run`

**Result:**
- Would discount **2,689 products**
- Total customer savings: **$6,359.23**
- Avg savings per item: **$2.36**
- Log: `data/logs/sale-layer1-dryrun-20260410_*.log`

### Problem 1 — too broad a sweep

2,689 products is a massive bulk action. The plan in `sale-wave-plan-april-2026.md` describes "first-time buyer psychology", but at this scale it's not a curated entry-point sale — it's effectively a sitewide discount on the bottom half of the catalog. That's the "10% off everything banner" the plan explicitly warned against.

A 200-300 product targeted sweep would be more credible. Suggested filters:
- Exclude shovelware (sports titles, licensed kid TV games, etc.) — they make up the bulk of the 2,689 and aren't searched for
- Limit to products with at least one organic Shopify pageview in the last 30 days (would need a separate analytics pull)
- OR: just `--top N` sorted by some popularity signal

### Problem 2 — $X.99 floor rounding makes "15% off" meaningless on cheap items

Many of the cheapest items get a discount of $0.01 - $0.10 because the script floors prices to the nearest $X.99. Examples from the dry-run:

| Product | Original | Sale | Save |
|---|---:|---:|---:|
| NBA All-Star Challenge - Sega Genesis | $6.00 | $5.99 | **$0.01** |
| ESPN Sunday Night NFL - Sega Genesis | $6.02 | $5.99 | $0.03 |
| Pipe Dreams 3D - PS1 | $6.02 | $5.99 | $0.03 |
| Play Action Football - NES | $4.00 | $3.99 | **$0.01** |
| Ski and Shoot - PS2 | $4.03 | $3.99 | $0.04 |
| Triple Play 99 - PS1 | $4.09 | $3.99 | $0.10 |

Customers seeing "**$0.01 off!**" feels worse than not advertising a sale at all. It's misleading and looks like a data glitch.

**Fix:** raise the price floor for Layer 1 (e.g., `--min-price 8 --max-price 20`), OR set a minimum dollar discount (e.g., `--min-savings 1.00`), OR change the floor from $X.99 to a real % calculation.

---

## Layer 2 — Deals of the Week, 20% off, 10 items

**Command:** `python3 scripts/manage-sales.py --deals-of-week 10 --discount 20 --dry-run`

**Result (10 random products picked):**

| Product | Original | Sale | Save |
|---|---:|---:|---:|
| Steel Battalion - Xbox | $529.99 | $423.99 | $106.00 |
| Superman - Sega Genesis | $95.99 | $76.99 | $19.00 |
| Venusaur (18/110) - Legendary Collection | $104.99 | $83.99 | $21.00 |
| Worldwide Soccer 98 - Sega Saturn | $22.99 | $18.99 | $4.00 |
| Super Mario Advance 2 - GBA | $26.99 | $21.99 | $5.00 |
| Bloodmoon Ursaluna ex - Prismatic Evolutions | $71.99 | $57.99 | $14.00 |
| WWF Royal Rumble - Dreamcast | $15.99 | $12.99 | $3.00 |
| El Tigre - PS2 | $12.99 | $10.99 | $2.00 |
| Spy Hunter Nowhere to Run - PS2 | $10.99 | $8.99 | $2.00 |
| Dave Mirra Freestyle BMX 2 - GameCube | $7.99 | $6.99 | $1.00 |

Total savings: $389

### Problem — selection is RANDOM, not iconic

The sale-wave plan said:
> "Selection: pick from sort-collections.py top-ranked titles (Mario, Zelda, Sonic, Final Fantasy, Castlevania, Metroid, Mega Man, Street Fighter, Pokemon)"

But the actual `--deals-of-week` flag in `manage-sales.py` just picks random products with `price >= 10` and no existing compare_at. The result is 10 random titles, including:
- A $529 Steel Battalion (way too expensive for an "impulse Deal of the Week")
- A Pokemon TCG single (already razor-thin margin per Layer 4 hands-off rule!)
- 4 obscure shovelware titles (Spy Hunter Nowhere to Run, Dave Mirra BMX 2, El Tigre, WWF Royal Rumble)

### Two violations of the plan
1. **Layer 4 hands-off list violated** — "Pokemon singles priced using 1.15x multiplier" should never be discounted, but Venusaur (Legendary Collection) and Bloodmoon Ursaluna got selected.
2. **Iconic-title selection logic missing** — the script doesn't consult the popularity ranking from `sort-collections.py`. It needs an `--iconic` mode that picks from the iconic-title list.

### Fix

Modify `manage-sales.py --deals-of-week` to:
- Exclude Pokemon cards by default (filter `category:pokemon_card` tag)
- Optionally filter by tags or a hardcoded iconic-title list (Mario, Zelda, Sonic, Final Fantasy, Castlevania, Metroid, Mega Man, Street Fighter)
- Add `--max-price` cap (e.g., $100) so we don't put a $530 game on a "deal of the week"

---

## Recommendation

**Do NOT run `manage-sales.py --apply` for either layer until both issues above are fixed.**

The sale wave is the right strategy. The implementation has bugs that would either (a) flood the store with meaningless $0.01 discounts or (b) put random shovelware and razor-margin Pokemon cards on the homepage hero.

**Next steps for terminal session:**
1. Patch `manage-sales.py` to add a `--min-savings` argument (default $1) and exclude Pokemon cards from `--deals-of-week`
2. Add an `--iconic` flag that filters by a hardcoded popular-franchise allowlist
3. Re-run dry-runs
4. Get user approval before any `--apply`

**Or if you'd rather:** I can write a separate `scripts/manage-iconic-sales.py` that does the curated logic without touching the existing script.
