import { NextResponse } from "next/server";
import { db } from "@db/index";
import { variants, products } from "@db/schema";
import { eq, isNull, lt, sql } from "drizzle-orm";

/**
 * GET /api/price-sync/staleness
 *
 * Report on price staleness across the product catalog.
 * Returns summary stats and the most stale products.
 */
export async function GET() {
  try {
    const now = Date.now();
    const oneDayAgo = new Date(now - 86400000).toISOString();
    const threeDaysAgo = new Date(now - 3 * 86400000).toISOString();
    const sevenDaysAgo = new Date(now - 7 * 86400000).toISOString();

    // Count variants by staleness
    const totalVariants = db
      .select({ count: sql<number>`count(*)` })
      .from(variants)
      .get()?.count ?? 0;

    const neverChecked = db
      .select({ count: sql<number>`count(*)` })
      .from(variants)
      .where(isNull(variants.lastPriceCheck))
      .get()?.count ?? 0;

    const staleOver24h = db
      .select({ count: sql<number>`count(*)` })
      .from(variants)
      .where(lt(variants.lastPriceCheck, oneDayAgo))
      .get()?.count ?? 0;

    const staleOver3d = db
      .select({ count: sql<number>`count(*)` })
      .from(variants)
      .where(lt(variants.lastPriceCheck, threeDaysAgo))
      .get()?.count ?? 0;

    const staleOver7d = db
      .select({ count: sql<number>`count(*)` })
      .from(variants)
      .where(lt(variants.lastPriceCheck, sevenDaysAgo))
      .get()?.count ?? 0;

    // Get the 20 most stale products that HAVE been checked before
    const mostStale = db
      .select({
        variantId: variants.shopifyVariantId,
        productId: variants.productShopifyId,
        title: variants.title,
        price: variants.price,
        lastPriceCheck: variants.lastPriceCheck,
        lastMarketPrice: variants.lastMarketPrice,
      })
      .from(variants)
      .where(lt(variants.lastPriceCheck, oneDayAgo))
      .orderBy(variants.lastPriceCheck)
      .limit(20)
      .all();

    return NextResponse.json({
      summary: {
        totalVariants,
        neverChecked,
        staleOver24h,
        staleOver3d,
        staleOver7d,
        freshWithin24h: totalVariants - neverChecked - staleOver24h,
      },
      mostStale,
    });
  } catch (error) {
    console.error("Failed to get staleness report:", error);
    return NextResponse.json({ error: "Failed to get staleness report" }, { status: 500 });
  }
}
