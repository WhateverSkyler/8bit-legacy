import { registerJob } from "./scheduler";
import { getShopifyConfig, getGoogleAdsConfig } from "./config";
import { fetchAllProducts, fetchUnfulfilledOrders } from "./shopify";
import { isGoogleAdsConfigured } from "./google-ads";
import { validateOrderPrices } from "./order-validator";
import { db } from "@db/index";
import { products, variants, orders, orderLineItems } from "@db/schema";
import { eq } from "drizzle-orm";

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

      // Call the sync endpoint internally
      const resp = await fetch("http://localhost:3001/api/google-ads/sync", { method: "POST" });
      const data = await resp.json();

      return {
        itemsProcessed: (data.synced?.campaigns ?? 0) + (data.synced?.products ?? 0),
        itemsChanged: data.synced?.searchTerms ?? 0,
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

  // ── Automated Price Sync ──────────────────────────────────────────
  registerJob({
    name: "price-sync",
    cron: "0 */6 * * *", // every 6 hours
    enabled: true,
    description: "Sync prices from PriceCharting and auto-apply safe changes",
    handler: async () => {
      const resp = await fetch("http://localhost:3001/api/automation/price-sync/run", {
        method: "POST",
      });
      const data = await resp.json();

      if (!data.success && data.error) {
        throw new Error(data.error);
      }

      return {
        itemsProcessed: data.summary?.totalMatched ?? 0,
        itemsChanged: data.summary?.autoApplied ?? 0,
        metadata: data.summary,
      };
    },
  });

  console.log("[Jobs] All automation jobs registered");
}
