import { registerJob } from "./scheduler";
import { getShopifyConfig, getGoogleAdsConfig } from "./config";
import { fetchAllProducts, fetchUnfulfilledOrders } from "./shopify";
import { isGoogleAdsConfigured } from "./google-ads";
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

      // Upsert products + variants
      let changed = 0;
      for (const sp of shopifyProducts) {
        const existing = db.select().from(products).where(eq(products.shopifyId, sp.id)).get();
        if (!existing) {
          db.insert(products).values({
            shopifyId: sp.id,
            title: sp.title,
            handle: sp.handle ?? "",
            vendor: sp.vendor ?? "",
            productType: sp.productType ?? "",
            tags: sp.productTags?.join(", ") ?? "",
            status: sp.status ?? "active",
            syncedAt: new Date().toISOString(),
          }).run();
          changed++;
        } else {
          db.update(products)
            .set({ title: sp.title, tags: sp.productTags?.join(", ") ?? "", syncedAt: new Date().toISOString() })
            .where(eq(products.shopifyId, sp.id))
            .run();
        }

        for (const v of sp.variants ?? []) {
          const existingV = db.select().from(variants).where(eq(variants.shopifyVariantId, v.id)).get();
          if (!existingV) {
            db.insert(variants).values({
              shopifyVariantId: v.id,
              productShopifyId: sp.id,
              title: v.title,
              sku: v.sku ?? "",
              price: parseFloat(v.price),
              compareAtPrice: v.compareAtPrice ? parseFloat(v.compareAtPrice) : null,
              inventoryQuantity: v.inventoryQuantity ?? 0,
            }).run();
          } else {
            db.update(variants)
              .set({
                price: parseFloat(v.price),
                compareAtPrice: v.compareAtPrice ? parseFloat(v.compareAtPrice) : null,
                inventoryQuantity: v.inventoryQuantity ?? 0,
              })
              .where(eq(variants.shopifyVariantId, v.id))
              .run();
          }
        }
      }

      return {
        itemsProcessed: shopifyProducts.length,
        itemsChanged: changed,
        metadata: { products: shopifyProducts.length, orders: shopifyOrders.length },
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

  // ── Fulfillment Check ─────────────────────────────────────────────
  registerJob({
    name: "fulfillment-check",
    cron: "*/30 * * * *", // every 30 minutes
    enabled: true,
    description: "Check for new unfulfilled Shopify orders",
    handler: async () => {
      const config = getShopifyConfig();
      if (!config.storeUrl || !config.accessToken) {
        return { itemsProcessed: 0, itemsChanged: 0, metadata: { skipped: "not configured" } };
      }

      const shopifyOrders = await fetchUnfulfilledOrders(config);

      return {
        itemsProcessed: shopifyOrders.length,
        itemsChanged: 0,
        metadata: { unfulfilledOrders: shopifyOrders.length },
      };
    },
  });

  console.log("[Jobs] All automation jobs registered");
}
