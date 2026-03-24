import { NextRequest, NextResponse } from "next/server";
import { getShopifyConfig } from "@/lib/config";
import { updateVariantPrice } from "@/lib/shopify";
import { db, schema } from "@db";

// POST /api/price-sync/apply — apply price changes to Shopify
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const changes: { variantId: string; newPrice: number; productTitle?: string; marketPrice?: number; oldPrice?: number; priceDiff?: number; estimatedProfit?: number }[] = body.changes;

    if (!changes || changes.length === 0) {
      return NextResponse.json(
        { error: "No changes to apply" },
        { status: 400 }
      );
    }

    const config = getShopifyConfig();

    if (!config.storeUrl || !config.accessToken) {
      // Demo mode: log to SQLite but don't call Shopify
      const netAdjustment = changes.reduce((sum, c) => sum + (c.priceDiff ?? 0), 0);

      try {
        const run = db.insert(schema.priceSyncRuns).values({
          timestamp: new Date().toISOString(),
          totalItems: changes.length,
          changesApplied: changes.length,
          belowProfit: 0,
          unmatched: 0,
          netAdjustment: Math.round(netAdjustment * 100) / 100,
        }).returning().get();

        for (const change of changes) {
          db.insert(schema.priceSyncItems).values({
            runId: run.id,
            productTitle: change.productTitle ?? "Unknown",
            variantId: change.variantId,
            marketPrice: change.marketPrice ?? 0,
            oldPrice: change.oldPrice ?? 0,
            newPrice: change.newPrice,
            priceDiff: change.priceDiff ?? 0,
            estimatedProfit: change.estimatedProfit ?? 0,
            status: "applied",
          }).run();
        }
      } catch {
        // DB logging is best-effort
      }

      return NextResponse.json({
        success: changes.length,
        failed: 0,
        errors: [],
        demo: true,
      });
    }

    const results = { success: 0, failed: 0, errors: [] as string[] };

    for (const change of changes) {
      const result = await updateVariantPrice(
        config,
        change.variantId,
        change.newPrice
      );

      if (result.success) {
        results.success++;
      } else {
        results.failed++;
        results.errors.push(
          `${change.variantId}: ${result.errors?.join(", ")}`
        );
      }

      // Rate limiting: ~4 requests/sec
      await new Promise((r) => setTimeout(r, 250));
    }

    // Log sync run to SQLite
    try {
      const netAdjustment = changes.reduce((sum, c) => sum + (c.priceDiff ?? 0), 0);
      const run = db.insert(schema.priceSyncRuns).values({
        timestamp: new Date().toISOString(),
        totalItems: changes.length,
        changesApplied: results.success,
        belowProfit: 0,
        unmatched: 0,
        netAdjustment: Math.round(netAdjustment * 100) / 100,
      }).returning().get();

      for (const change of changes) {
        db.insert(schema.priceSyncItems).values({
          runId: run.id,
          productTitle: change.productTitle ?? "Unknown",
          variantId: change.variantId,
          marketPrice: change.marketPrice ?? 0,
          oldPrice: change.oldPrice ?? 0,
          newPrice: change.newPrice,
          priceDiff: change.priceDiff ?? 0,
          estimatedProfit: change.estimatedProfit ?? 0,
          status: results.errors.some((e) => e.startsWith(change.variantId)) ? "failed" : "applied",
        }).run();
      }
    } catch {
      // DB logging is best-effort
    }

    return NextResponse.json(results);
  } catch (error) {
    console.error("Price apply error:", error);
    return NextResponse.json(
      { error: "Failed to apply price changes" },
      { status: 500 }
    );
  }
}
