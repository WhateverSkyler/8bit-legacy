import "server-only";
import { db } from "@db/index";
import { variants, products } from "@db/schema";
import { eq, asc, isNull, or, sql } from "drizzle-orm";
import { getPricingConfig, getShopifyConfig } from "./config";
import { updateVariantPrice } from "./shopify";
import { checkPriceChangeSafety, isCircuitBreakerTripped } from "./safety";

const PRICECHARTING_SEARCH = "https://www.pricecharting.com/search-products";
const SEARCH_DELAY = 2500; // 2.5s between searches (respectful)
const BATCH_SIZE = 100; // Products per scheduler run (~4 min)
const MAX_MARKET_PRICE = 800; // Skip results above this (likely bad matches or ultra-rare variants)

interface SearchResult {
  title: string;
  console: string;
  loose: number;
  cib: number;
}

/**
 * Score how well a PriceCharting result title matches the search query.
 * Returns 0-1, higher is better. Penalizes sequels and variants.
 */
function titleSimilarity(queryTitle: string, resultTitle: string): number {
  const normalize = (s: string) =>
    s.toLowerCase().replace(/[^a-z0-9 ]/g, "").split(/\s+/).filter(Boolean);

  const queryWords = new Set(normalize(queryTitle));
  // Strip console suffix from result title
  const cleanResult = resultTitle
    .replace(/(NES|SNES|Nintendo 64|Gamecube|Gameboy|Genesis|Playstation|PS[123]|Dreamcast|Saturn|GBA|Xbox|Wii|Sega|Atari|TurboGrafx|GameBoy|Game Boy).*$/i, "")
    .trim();
  const resultWords = new Set(normalize(cleanResult));

  if (queryWords.size === 0 || resultWords.size === 0) return 0;

  const extraWords = new Set([...resultWords].filter((w) => !queryWords.has(w)));
  const sequelIndicators = new Set([
    "2", "3", "4", "5", "6", "7", "8", "9",
    "ii", "iii", "iv", "part", "second", "math",
    "assassin", "case", "screw", "attack", "special",
    "edition", "deluxe", "bundle", "collection",
  ]);

  for (const word of extraWords) {
    if (sequelIndicators.has(word)) return 0.1;
  }

  const common = [...queryWords].filter((w) => resultWords.has(w));
  let score = common.length / Math.max(queryWords.size, resultWords.size);
  if (extraWords.size > 0) score *= Math.max(0.5, 1.0 - extraWords.size * 0.2);
  return score;
}

/**
 * Refresh game prices by searching PriceCharting for the most stale products.
 *
 * Each run processes BATCH_SIZE products, prioritizing those that haven't
 * been checked in the longest time (or never checked). Over multiple runs,
 * this covers the entire catalog.
 */
export async function refreshGamePricesBatch(): Promise<{
  success: boolean;
  searched: number;
  matched: number;
  looseUpdated: number;
  cibUpdated: number;
  errors: number;
}> {
  const breaker = isCircuitBreakerTripped("pricing");
  if (breaker.tripped) {
    throw new Error(`Pricing circuit breaker tripped: ${breaker.reason}`);
  }

  const config = getPricingConfig();
  const shopifyConfig = getShopifyConfig();
  if (!shopifyConfig.storeUrl || !shopifyConfig.accessToken) {
    return { success: false, searched: 0, matched: 0, looseUpdated: 0, cibUpdated: 0, errors: 0 };
  }

  // Get the most stale products (oldest lastPriceCheck first, nulls first)
  const staleProducts = db
    .select({
      shopifyId: products.shopifyId,
      title: products.title,
      tags: products.tags,
    })
    .from(products)
    .orderBy(asc(sql`COALESCE((SELECT v.last_price_check FROM variants v WHERE v.product_id = products.id LIMIT 1), '2000-01-01')`))
    .limit(BATCH_SIZE)
    .all();

  if (staleProducts.length === 0) {
    return { success: true, searched: 0, matched: 0, looseUpdated: 0, cibUpdated: 0, errors: 0 };
  }

  // Console tag mapping
  const TAG_TO_CONSOLE: Record<string, string> = {
    "nes": "NES", "nes (nintendo entertainment system)": "NES",
    "snes": "SNES", "snes (super nintendo entertainment system)": "SNES",
    "super nintendo": "SNES", "nintendo 64": "Nintendo 64", "n64": "Nintendo 64",
    "gamecube": "Gamecube", "nintendo gamecube": "Gamecube",
    "nintendo gamecube > gamecube": "Gamecube",
    "wii": "Wii", "wii u": "Wii U",
    "gameboy": "Gameboy", "gameboy color": "Gameboy Color",
    "gameboy advance": "Gameboy Advance", "gba": "Gameboy Advance",
    "nintendo ds": "Nintendo DS", "nintendo 3ds": "Nintendo 3DS",
    "sega genesis": "Sega Genesis", "genesis": "Sega Genesis",
    "sega saturn": "Sega Saturn", "sega dreamcast": "Sega Dreamcast",
    "sega master system": "Sega Master System",
    "sega cd": "Sega CD", "sega 32x": "Sega 32X",
    "playstation": "Playstation", "ps1": "Playstation",
    "playstation 2": "Playstation 2", "ps2": "Playstation 2",
    "playstation 3": "Playstation 3", "psp": "PSP",
    "xbox": "Xbox", "xbox 360": "Xbox 360",
    "atari 2600": "Atari 2600",
  };

  let searched = 0;
  let matched = 0;
  let looseUpdated = 0;
  let cibUpdated = 0;
  let errors = 0;
  const now = new Date().toISOString();

  for (const product of staleProducts) {
    // Find console from tags
    const tags = (product.tags || "").split(",").map((t: string) => t.trim());
    let consoleName: string | null = null;
    for (const tag of tags) {
      const cn = TAG_TO_CONSOLE[tag.toLowerCase()];
      if (cn) {
        consoleName = cn;
        break;
      }
    }

    if (!consoleName) continue;

    // Strip console suffix from title
    const gameTitle = product.title
      .replace(/\s*[-–]\s*(NES|SNES|N64|Nintendo|Gameboy|Game Boy|Genesis|PS[123P]|Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii|Sega|Atari|TurboGrafx|GBC).*$/i, "")
      .trim();

    // Search PriceCharting
    const result = await searchPriceCharting(gameTitle, consoleName);
    searched++;

    if (!result) {
      // Still update lastPriceCheck so we don't keep retrying immediately
      const productVariants = db
        .select()
        .from(variants)
        .where(eq(variants.productShopifyId, product.shopifyId))
        .all();

      for (const v of productVariants) {
        db.update(variants)
          .set({ lastPriceCheck: now })
          .where(eq(variants.shopifyVariantId, v.shopifyVariantId))
          .run();
      }
      continue;
    }

    matched++;

    // Get variants for this product
    const productVariants = db
      .select()
      .from(variants)
      .where(eq(variants.productShopifyId, product.shopifyId))
      .all();

    for (const variant of productVariants) {
      const vTitle = (variant.title || "").toLowerCase();
      const isCib = vTitle.includes("complete") || vTitle.includes("cib") || vTitle.includes("box");
      const market = isCib ? result.cib : result.loose;

      if (!market || market <= 0) continue;

      // Calculate sell price
      const multiplier = config.category_multipliers?.retro_games ?? config.default_multiplier;
      let sellPrice = market * multiplier;
      if (config.round_to != null) {
        sellPrice = Math.ceil(sellPrice) - (1 - config.round_to);
        if (sellPrice < market * multiplier) sellPrice += 1.0;
      }
      sellPrice = Math.round(sellPrice * 100) / 100;

      const diff = Math.abs(sellPrice - variant.price);
      if (diff < 0.50) {
        // No significant change — just update staleness
        db.update(variants)
          .set({ lastPriceCheck: now, lastMarketPrice: market })
          .where(eq(variants.shopifyVariantId, variant.shopifyVariantId))
          .run();
        continue;
      }

      // Safety check
      const safety = checkPriceChangeSafety(variant.price, sellPrice);
      if (safety.action === "rejected") continue;
      if (safety.action === "needs_review") continue;

      // Apply if auto-apply enabled
      if (config.auto_apply_enabled) {
        const res = await updateVariantPrice(shopifyConfig, variant.shopifyVariantId, sellPrice);
        if (res.success) {
          if (isCib) cibUpdated++;
          else looseUpdated++;
        } else {
          errors++;
        }
        await new Promise((r) => setTimeout(r, 300));
      }

      db.update(variants)
        .set({
          price: config.auto_apply_enabled ? sellPrice : variant.price,
          lastPriceCheck: now,
          lastMarketPrice: market,
        })
        .where(eq(variants.shopifyVariantId, variant.shopifyVariantId))
        .run();
    }

    await new Promise((r) => setTimeout(r, SEARCH_DELAY));
  }

  return { success: true, searched, matched, looseUpdated, cibUpdated, errors };
}

async function searchPriceCharting(gameTitle: string, consoleName: string): Promise<SearchResult | null> {
  const query = `${gameTitle} ${consoleName}`;
  const url = `${PRICECHARTING_SEARCH}?q=${encodeURIComponent(query)}&type=videogames`;

  try {
    const resp = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        Accept: "text/html",
      },
    });

    if (!resp.ok) return null;

    const html = await resp.text();

    // Parse with regex (no DOM parser in Node server-side without extra deps)
    const tableMatch = html.match(/<table[^>]*id="games_table"[^>]*>([\s\S]*?)<\/table>/i);
    if (!tableMatch) return null;

    const tbodyMatch = tableMatch[1].match(/<tbody>([\s\S]*?)<\/tbody>/i);
    if (!tbodyMatch) return null;

    const rows = tbodyMatch[1].match(/<tr[\s\S]*?<\/tr>/gi);
    if (!rows) return null;

    const targetConsole = consoleName.toLowerCase();
    const extractPrice = (cell: string): number => {
      const m = cell.replace(/<[^>]+>/g, "").replace(/[$,]/g, "").trim().match(/([\d.]+)/);
      return m ? parseFloat(m[1]) : 0;
    };

    // Collect candidates and pick best title match
    const candidates: (SearchResult & { similarity: number })[] = [];

    for (const row of rows.slice(0, 8)) {
      const cells = row.match(/<td[\s\S]*?<\/td>/gi);
      if (!cells || cells.length < 5) continue;

      const consoleText = cells[2].replace(/<[^>]+>/g, "").trim().toLowerCase();

      if (consoleText.includes("pal") || consoleText.includes("jp ") || consoleText.includes("japanese")) {
        continue;
      }

      if (!consoleText.includes(targetConsole) && !targetConsole.includes(consoleText)) {
        continue;
      }

      const titleMatch = cells[1].match(/<a[^>]*>([^<]+)<\/a>/i);
      const title = titleMatch ? titleMatch[1].trim() : "";

      candidates.push({
        title,
        console: consoleText,
        loose: extractPrice(cells[3]),
        cib: extractPrice(cells[4]),
        similarity: titleSimilarity(gameTitle, title),
      });
    }

    if (candidates.length === 0) return null;

    // Pick best title match (minimum 0.3 similarity)
    const best = candidates.reduce((a, b) => (a.similarity > b.similarity ? a : b));
    if (best.similarity < 0.3) return null;

    // Cap extremely high prices
    return {
      title: best.title,
      console: best.console,
      loose: best.loose > MAX_MARKET_PRICE ? 0 : best.loose,
      cib: best.cib > MAX_MARKET_PRICE ? 0 : best.cib,
    };
  } catch (err) {
    console.error(`[Game Price Sync] Search failed for "${gameTitle}":`, err);
  }

  return null;
}
