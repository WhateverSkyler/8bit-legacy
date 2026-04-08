import { registerJob } from "./scheduler";
import { getShopifyConfig, getGoogleAdsConfig } from "./config";
import { fetchAllProducts, fetchUnfulfilledOrders } from "./shopify";
import { isGoogleAdsConfigured } from "./google-ads";
import { validateOrderPrices } from "./order-validator";
import { refreshPokemonCardPrices } from "./pokemon-price-sync";
import { refreshGamePricesBatch } from "./game-price-sync";
import { db } from "@db/index";
import { products, variants, orders, orderLineItems } from "@db/schema";
import { eq, like } from "drizzle-orm";

/**
 * Register all automation jobs. Called once at server startup.
 */
export function registerAllJobs(): void {
  // ── Shopify Product Sync ──────────────────────────────────────────
  registerJob({
    name: "shopify-product-sync",
    cron: "0 */4 * * *", // every 4 hours
    enabled: true,
    description: "Sync products and orders from Shopify into local DB",
    handler: async () => {
      const config = getShopifyConfig();
      if (!config.storeUrl || !config.accessToken) {
        return { itemsProcessed: 0, itemsChanged: 0, metadata: { skipped: "not configured" } };
      }

      const [shopifyProducts, shopifyOrders] = await Promise.all([
        fetchAllProducts(config),
        fetchUnfulfilledOrders(config),
      ]);

      // fetchAllProducts returns flat per-variant entries — group by product first
      const productMap = new Map<string, typeof shopifyProducts>();
      for (const sp of shopifyProducts) {
        const group = productMap.get(sp.productId) ?? [];
        group.push(sp);
        productMap.set(sp.productId, group);
      }

      // Upsert products + variants
      let changed = 0;
      const now = new Date().toISOString();

      for (const [productId, entries] of productMap) {
        const first = entries[0];
        const existing = db.select().from(products).where(eq(products.shopifyId, productId)).get();

        if (!existing) {
          db.insert(products).values({
            shopifyId: productId,
            title: first.productTitle,
            handle: first.productHandle,
            tags: first.productTags?.join(", ") ?? "",
            syncedAt: now,
          }).run();
          changed++;
        } else {
          db.update(products)
            .set({
              title: first.productTitle,
              tags: first.productTags?.join(", ") ?? "",
              syncedAt: now,
            })
            .where(eq(products.shopifyId, productId))
            .run();
        }

        // Upsert each variant
        for (const sp of entries) {
          const existingV = db.select().from(variants).where(eq(variants.shopifyVariantId, sp.variantId)).get();
          if (!existingV) {
            db.insert(variants).values({
              shopifyVariantId: sp.variantId,
              productShopifyId: productId,
              title: sp.variantTitle,
              sku: sp.sku,
              price: sp.currentPrice,
              barcode: sp.barcode,
              syncedAt: now,
            }).run();
          } else {
            db.update(variants)
              .set({
                price: sp.currentPrice,
                barcode: sp.barcode,
                syncedAt: now,
              })
              .where(eq(variants.shopifyVariantId, sp.variantId))
              .run();
          }
        }
      }

      return {
        itemsProcessed: productMap.size,
        itemsChanged: changed,
        metadata: { products: productMap.size, variants: shopifyProducts.length, orders: shopifyOrders.length },
      };
    },
  });

  // ── Google Ads Performance Sync ───────────────────────────────────
  registerJob({
    name: "google-ads-sync",
    cron: "0 1 * * *", // daily at 1 AM ET
    enabled: true,
    description: "Pull campaign performance data from Google Ads",
    handler: async () => {
      const config = getGoogleAdsConfig();
      if (!isGoogleAdsConfigured(config)) {
        return { itemsProcessed: 0, itemsChanged: 0, metadata: { skipped: "not configured" } };
      }

      const resp = await fetch("http://localhost:3001/api/google-ads/sync", {
        method: "POST",
        signal: AbortSignal.timeout(60_000),
      });

      if (!resp.ok) {
        throw new Error(`Google Ads sync API returned ${resp.status}: ${resp.statusText}`);
      }

      const data = await resp.json();
      if (!data.synced) {
        throw new Error("Google Ads sync response missing 'synced' data");
      }

      return {
        itemsProcessed: (data.synced.campaigns ?? 0) + (data.synced.products ?? 0),
        itemsChanged: data.synced.searchTerms ?? 0,
        metadata: data.synced,
      };
    },
  });

  // ── Fulfillment Check + Order Price Validation ────────────────────
  registerJob({
    name: "fulfillment-check",
    cron: "*/30 * * * *", // every 30 minutes
    enabled: true,
    description: "Check for new unfulfilled orders and validate prices against market",
    handler: async () => {
      const config = getShopifyConfig();
      if (!config.storeUrl || !config.accessToken) {
        return { itemsProcessed: 0, itemsChanged: 0, metadata: { skipped: "not configured" } };
      }

      const shopifyOrders = await fetchUnfulfilledOrders(config);

      // Validate order prices against current market data
      const validation = validateOrderPrices(shopifyOrders);

      if (validation.losses > 0) {
        console.warn(
          `[Fulfillment] WARNING: ${validation.losses} order items would be sold at a LOSS!`
        );
      }

      return {
        itemsProcessed: shopifyOrders.length,
        itemsChanged: validation.alertsCreated,
        metadata: {
          unfulfilledOrders: shopifyOrders.length,
          itemsValidated: validation.validated,
          losses: validation.losses,
          thinMargins: validation.thinMargins,
          alertsCreated: validation.alertsCreated,
        },
      };
    },
  });

  // ── Automated Game Price Sync (Search-Based) ──────────────────────
  registerJob({
    name: "price-sync",
    cron: "0 */4 * * *", // every 4 hours
    enabled: true,
    description: "Refresh game prices from PriceCharting (100 most stale products per run)",
    handler: async () => {
      const result = await refreshGamePricesBatch();

      return {
        itemsProcessed: result.searched,
        itemsChanged: result.looseUpdated + result.cibUpdated,
        metadata: {
          searched: result.searched,
          matched: result.matched,
          looseUpdated: result.looseUpdated,
          cibUpdated: result.cibUpdated,
          errors: result.errors,
        },
      };
    },
  });

  // ── Pokemon Card Price Refresh ────────────────────────────────────
  registerJob({
    name: "pokemon-price-sync",
    cron: "0 3,15 * * *", // twice daily at 3 AM and 3 PM ET
    enabled: true,
    description: "Refresh Pokemon card prices from TCGPlayer via Pokemon TCG API",
    handler: async () => {
      // Only run if we have Pokemon cards in the DB
      const pokemonCount = db
        .select({ count: variants.shopifyVariantId })
        .from(variants)
        .where(like(variants.sku, "PKM-%"))
        .all().length;

      if (pokemonCount === 0) {
        return { itemsProcessed: 0, itemsChanged: 0, metadata: { skipped: "no pokemon cards in DB" } };
      }

      const result = await refreshPokemonCardPrices();

      return {
        itemsProcessed: result.cardsChecked,
        itemsChanged: result.pricesUpdated,
        metadata: {
          setsChecked: result.setsChecked,
          cardsChecked: result.cardsChecked,
          pricesUpdated: result.pricesUpdated,
          needsReview: result.needsReview,
          rejected: result.rejected,
          errors: result.errors,
        },
      };
    },
  });

  console.log("[Jobs] All automation jobs registered");
}
