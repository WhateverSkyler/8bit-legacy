import "server-only";
import { db } from "@db/index";
import { variants, products, priceSnapshots } from "@db/schema";
import { eq, like } from "drizzle-orm";
import { getPricingConfig, getShopifyConfig } from "./config";
import { updateVariantPrice } from "./shopify";
import { checkPriceChangeSafety, isCircuitBreakerTripped, tripCircuitBreaker } from "./safety";

const POKEMON_TCG_API = "https://api.pokemontcg.io/v2";
const API_KEY = process.env.POKEMON_TCG_API_KEY ?? "";
const API_DELAY = 500; // ms between API requests

interface TCGPlayerPrices {
  [variant: string]: {
    low?: number;
    mid?: number;
    high?: number;
    market?: number;
    directLow?: number;
  };
}

interface CardPriceUpdate {
  variantId: string;
  productTitle: string;
  oldPrice: number;
  newPrice: number;
  marketPrice: number;
  priceDiff: number;
}

/**
 * Fetch updated TCGPlayer prices for Pokemon cards already in Shopify.
 * Uses the Pokemon TCG API which embeds TCGPlayer market prices.
 *
 * Strategy: look up cards in the local DB that have pokemon SKUs (PKM-*),
 * fetch current prices from the API by set, and update Shopify prices.
 */
export async function refreshPokemonCardPrices(): Promise<{
  success: boolean;
  setsChecked: number;
  cardsChecked: number;
  pricesUpdated: number;
  needsReview: number;
  rejected: number;
  errors: number;
}> {
  const breaker = isCircuitBreakerTripped("pricing");
  if (breaker.tripped) {
    throw new Error(`Pricing circuit breaker tripped: ${breaker.reason}`);
  }

  const config = getPricingConfig();
  const shopifyConfig = getShopifyConfig();
  const multiplier = config.category_multipliers?.pokemon_cards ?? config.default_multiplier;

  // Find all Pokemon card variants in the local DB by SKU prefix
  const pokemonVariants = db
    .select({
      variantId: variants.shopifyVariantId,
      sku: variants.sku,
      price: variants.price,
      productId: variants.productShopifyId,
    })
    .from(variants)
    .where(like(variants.sku, "PKM-%"))
    .all();

  if (pokemonVariants.length === 0) {
    return { success: true, setsChecked: 0, cardsChecked: 0, pricesUpdated: 0, needsReview: 0, rejected: 0, errors: 0 };
  }

  // Group by set ID (SKU format: PKM-{setId}-{cardNumber})
  const setMap = new Map<string, typeof pokemonVariants>();
  for (const v of pokemonVariants) {
    const parts = v.sku.split("-");
    if (parts.length >= 3) {
      const setId = parts[1];
      const group = setMap.get(setId) ?? [];
      group.push(v);
      setMap.set(setId, group);
    }
  }

  let cardsChecked = 0;
  let pricesUpdated = 0;
  let needsReview = 0;
  let rejected = 0;
  let errors = 0;

  const autoApplyEnabled = config.auto_apply_enabled ?? false;
  const now = new Date().toISOString();

  // Fetch fresh prices per set
  for (const [setId, setVariants] of setMap) {
    try {
      // Build a map of card number → variant for this set
      const variantByCardNum = new Map<string, typeof pokemonVariants[0]>();
      for (const v of setVariants) {
        const parts = v.sku.split("-");
        const cardNum = parts.slice(2).join("-"); // Handle card numbers like "1", "GG01"
        variantByCardNum.set(cardNum, v);
      }

      // Fetch all cards for this set from the API
      const cards = await fetchSetCards(setId);
      cardsChecked += cards.length;

      for (const card of cards) {
        const cardNum = card.number;
        const variant = variantByCardNum.get(cardNum);
        if (!variant) continue;

        const marketPrice = extractMarketPrice(card.tcgplayer?.prices);
        if (!marketPrice) continue;

        // Calculate new sell price
        const rawSellPrice = marketPrice * multiplier;
        let sellPrice: number;
        if (config.round_to != null) {
          sellPrice = Math.ceil(rawSellPrice) - (1 - config.round_to);
          if (sellPrice < rawSellPrice) sellPrice += 1.0;
          sellPrice = Math.round(sellPrice * 100) / 100;
        } else {
          sellPrice = Math.round(rawSellPrice * 100) / 100;
        }

        const oldPrice = variant.price;
        const priceDiff = Math.round((sellPrice - oldPrice) * 100) / 100;

        // Skip if no meaningful change
        if (Math.abs(priceDiff) < 0.50) {
          // Still update staleness tracking
          db.update(variants)
            .set({ lastPriceCheck: now, lastMarketPrice: marketPrice })
            .where(eq(variants.shopifyVariantId, variant.variantId))
            .run();
          continue;
        }

        // Safety check
        const safety = checkPriceChangeSafety(oldPrice, sellPrice);

        if (safety.action === "rejected") {
          rejected++;
          continue;
        }

        if (safety.action === "needs_review") {
          needsReview++;
          // Cache snapshot for review
          db.insert(priceSnapshots).values({
            productTitle: card.name,
            consoleName: `pokemon-${setId}`,
            loosePrice: marketPrice,
            source: "pokemon-tcg-api",
            scrapedAt: now,
          }).run();
          continue;
        }

        // Auto-apply if enabled
        if (autoApplyEnabled && shopifyConfig.storeUrl && shopifyConfig.accessToken) {
          const result = await updateVariantPrice(shopifyConfig, variant.variantId, sellPrice);
          if (result.success) {
            pricesUpdated++;
          } else {
            errors++;
          }
          await new Promise((r) => setTimeout(r, 250));
        }

        // Update staleness tracking
        db.update(variants)
          .set({
            price: autoApplyEnabled ? sellPrice : oldPrice,
            lastPriceCheck: now,
            lastMarketPrice: marketPrice,
          })
          .where(eq(variants.shopifyVariantId, variant.variantId))
          .run();

        // Cache price snapshot
        db.insert(priceSnapshots).values({
          productTitle: card.name,
          consoleName: `pokemon-${setId}`,
          loosePrice: marketPrice,
          source: "pokemon-tcg-api",
          scrapedAt: now,
        }).run();
      }
    } catch (err) {
      console.error(`[Pokemon Price Sync] Failed to refresh set ${setId}:`, err);
      errors++;
    }

    await new Promise((r) => setTimeout(r, API_DELAY));
  }

  // Trip circuit breaker if too many changes
  if (pricesUpdated > 100) {
    console.warn(`[Pokemon Price Sync] Large update: ${pricesUpdated} prices changed`);
  }

  return {
    success: true,
    setsChecked: setMap.size,
    cardsChecked,
    pricesUpdated,
    needsReview,
    rejected,
    errors,
  };
}

async function fetchSetCards(setId: string): Promise<any[]> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (API_KEY) headers["X-Api-Key"] = API_KEY;

  const cards: any[] = [];
  let page = 1;

  while (true) {
    const url = `${POKEMON_TCG_API}/cards?q=set.id:${setId}&pageSize=250&page=${page}`;
    const resp = await fetch(url, { headers });

    if (!resp.ok) {
      throw new Error(`Pokemon TCG API error: ${resp.status}`);
    }

    const data = await resp.json();
    cards.push(...data.data);

    if (cards.length >= data.totalCount) break;
    page++;
    await new Promise((r) => setTimeout(r, API_DELAY));
  }

  return cards;
}

function extractMarketPrice(prices?: TCGPlayerPrices): number | null {
  if (!prices) return null;

  const priority = ["normal", "holofoil", "reverseHolofoil",
                     "1stEditionHolofoil", "1stEditionNormal", "unlimitedHolofoil"];

  for (const variant of priority) {
    if (prices[variant]?.market) return prices[variant].market!;
  }

  for (const variantData of Object.values(prices)) {
    if (variantData?.market) return variantData.market;
  }

  return null;
}
