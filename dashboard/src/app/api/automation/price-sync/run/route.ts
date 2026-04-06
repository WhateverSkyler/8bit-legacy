import { NextResponse } from "next/server";
import { db } from "@db/index";
import { priceSnapshots, priceSyncRuns, priceSyncItems, googleAdsPerformance, variants } from "@db/schema";
import { desc, eq, gte, sql } from "drizzle-orm";
import { getShopifyConfig, getPricingConfig } from "@/lib/config";
import { fetchAllProducts, updateVariantPrice } from "@/lib/shopify";
import { matchProducts, generateDiff, type ShopifyProduct } from "@/lib/matching";
import { runPython } from "@/lib/python-bridge";
import { checkPriceChangeSafety, isCircuitBreakerTripped, tripCircuitBreaker } from "@/lib/safety";
import { calculateProfitWithAdCost } from "@/lib/pricing";
import type { PriceChartingItem } from "@/types/product";

/**
 * POST /api/automation/price-sync/run
 *
 * Full automated pricing run:
 * 1. Scrape PriceCharting via Python bridge
 * 2. Match to Shopify products
 * 3. Generate diff with safety checks
 * 4. Auto-apply safe changes, queue risky ones for review
 * 5. Log everything
 */
export async function POST() {
  try {
    // Check circuit breaker
    const breaker = isCircuitBreakerTripped("pricing");
    if (breaker.tripped) {
      return NextResponse.json(
        { error: `Pricing circuit breaker is tripped: ${breaker.reason}` },
        { status: 423 }
      );
    }

    const pricingConfig = getPricingConfig();
    const shopifyConfig = getShopifyConfig();

    // Step 1: Get Shopify products
    let shopifyProducts: ShopifyProduct[] = [];

    if (shopifyConfig.storeUrl && shopifyConfig.accessToken) {
      shopifyProducts = await fetchAllProducts(shopifyConfig);
    } else {
      return NextResponse.json({ error: "Shopify not configured" }, { status: 400 });
    }

    // Step 2: Scrape PriceCharting for all products
    // Use the scraper with --from-file approach: generate a temp list of product titles
    // For now, use existing price snapshots if recent, otherwise scrape
    const oneDayAgo = new Date(Date.now() - 86400000).toISOString();
    const recentSnapshots = db
      .select()
      .from(priceSnapshots)
      .where(gte(priceSnapshots.scrapedAt, oneDayAgo))
      .all();

    let pcItems: PriceChartingItem[] = [];

    if (recentSnapshots.length > 0) {
      // Use cached snapshots
      pcItems = recentSnapshots.map((s) => ({
        name: s.productTitle,
        console: s.consoleName,
        loosePrice: s.loosePrice,
        cibPrice: s.cibPrice ?? 0,
        newPrice: s.newPrice ?? 0,
        upc: "",
        asin: "",
      }));
    } else {
      // Run the scraper for each unique console in inventory
      const consoles = new Set<string>();
      for (const sp of shopifyProducts) {
        for (const tag of sp.productTags) {
          const lower = tag.toLowerCase();
          if (["nes", "snes", "n64", "gameboy", "genesis", "ps1", "ps2", "gamecube", "dreamcast", "saturn", "gba", "pokemon", "pokemon-cards", "pokemon_cards", "tcg"].includes(lower)) {
            consoles.add(lower);
          }
        }
      }

      // Scrape each console (limited pages for speed)
      const POKEMON_TAGS = new Set(["pokemon", "pokemon-cards", "pokemon_cards", "tcg"]);
      for (const consoleName of consoles) {
        try {
          const isPokemon = POKEMON_TAGS.has(consoleName);
          const scraperArgs = ["--console", consoleName, "--pages", "3", "--save"];
          if (isPokemon) {
            scraperArgs.push("--type", "trading-cards");
          }
          const result = await runPython(
            "pricecharting-scraper.py",
            scraperArgs,
            60000
          );

          if (result.exitCode === 0 && result.stdout) {
            // Parse the scraper output (CSV-like) and store as snapshots
            const lines = result.stdout.trim().split("\n");
            for (const line of lines.slice(1)) {
              // Skip header
              const parts = line.split(",");
              if (parts.length >= 3) {
                const title = parts[0]?.trim();
                const loose = parseFloat(parts[2]) || 0;
                const cib = parseFloat(parts[3]) || 0;
                const newP = parseFloat(parts[4]) || 0;

                if (title && loose > 0) {
                  pcItems.push({
                    name: title,
                    console: consoleName,
                    loosePrice: loose,
                    cibPrice: cib,
                    newPrice: newP,
                    upc: "",
                    asin: "",
                  });

                  // Cache to DB
                  db.insert(priceSnapshots)
                    .values({
                      productTitle: title,
                      consoleName,
                      loosePrice: loose,
                      cibPrice: cib,
                      newPrice: newP,
                      source: "scraper",
                      scrapedAt: new Date().toISOString(),
                    })
                    .run();
                }
              }
            }
          }
        } catch (err) {
          console.error(`Scraper failed for ${consoleName}:`, err);
        }
      }
    }

    if (pcItems.length === 0) {
      return NextResponse.json({
        success: true,
        message: "No pricing data available to sync",
        itemsProcessed: 0,
        itemsChanged: 0,
      });
    }

    // Step 3: Match and generate diff
    const { matches, unmatched } = matchProducts(pcItems, shopifyProducts);
    const { changes, skippedProfit, noChange } = generateDiff(matches, pricingConfig);

    // Step 4: Calculate ad cost per order if enabled
    let adCostPerOrder = 0;
    if (pricingConfig.factor_ad_spend) {
      const lookbackDays = pricingConfig.ad_cost_lookback_days ?? 30;
      const lookbackDate = new Date(Date.now() - lookbackDays * 86400000).toISOString();

      const adData = db
        .select({
          totalCost: sql<number>`sum(cost)`,
          totalConversions: sql<number>`sum(conversions)`,
        })
        .from(googleAdsPerformance)
        .where(gte(googleAdsPerformance.date, lookbackDate))
        .get();

      if (adData && adData.totalConversions && adData.totalConversions > 0) {
        adCostPerOrder = (adData.totalCost ?? 0) / adData.totalConversions;
      }
    }

    // Step 5: Apply safety checks and auto-apply
    const autoApplied: typeof changes = [];
    const needsReview: typeof changes = [];
    const rejected: typeof changes = [];

    for (const change of changes) {
      const safety = checkPriceChangeSafety(change.currentShopifyPrice, change.newPrice);

      if (safety.action === "rejected") {
        rejected.push(change);
      } else if (safety.action === "needs_review") {
        needsReview.push(change);
      } else {
        // If factoring ad cost, check profit still meets threshold
        if (adCostPerOrder > 0) {
          const trueProfit = calculateProfitWithAdCost(
            change.newPrice,
            change.marketPrice,
            pricingConfig,
            adCostPerOrder
          );
          if (trueProfit < pricingConfig.minimum_profit_usd) {
            needsReview.push(change);
            continue;
          }
        }
        autoApplied.push(change);
      }
    }

    // Circuit breaker: if too many large changes, abort
    const largeChanges = autoApplied.filter(
      (c) => Math.abs(c.priceDiff) / c.currentShopifyPrice > 0.15
    );
    if (largeChanges.length > 20) {
      tripCircuitBreaker(
        "pricing",
        `${largeChanges.length} items had >15% price changes in a single run`
      );
      return NextResponse.json({
        error: "Circuit breaker tripped: too many large price changes",
        largeChanges: largeChanges.length,
      }, { status: 423 });
    }

    // Step 6: Apply to Shopify
    let successCount = 0;
    let failCount = 0;

    if (pricingConfig.auto_apply_enabled && autoApplied.length > 0) {
      for (const change of autoApplied) {
        const result = await updateVariantPrice(
          shopifyConfig,
          change.variantId,
          change.newPrice
        );
        if (result.success) {
          successCount++;
        } else {
          failCount++;
        }
        await new Promise((r) => setTimeout(r, 250));
      }
    }

    // Step 7: Log to DB
    const netAdjustment = autoApplied.reduce((sum, c) => sum + c.priceDiff, 0);
    const run = db
      .insert(priceSyncRuns)
      .values({
        timestamp: new Date().toISOString(),
        totalItems: matches.length,
        changesApplied: successCount,
        belowProfit: skippedProfit.length,
        unmatched: unmatched.length,
        netAdjustment: Math.round(netAdjustment * 100) / 100,
      })
      .returning()
      .get();

    for (const change of [...autoApplied, ...needsReview, ...rejected]) {
      const status = autoApplied.includes(change)
        ? "applied"
        : needsReview.includes(change)
          ? "needs_review"
          : "rejected";

      db.insert(priceSyncItems)
        .values({
          runId: run.id,
          productTitle: change.productTitle,
          variantId: change.variantId,
          marketPrice: change.marketPrice,
          oldPrice: change.currentShopifyPrice,
          newPrice: change.newPrice,
          priceDiff: change.priceDiff,
          estimatedProfit: change.estimatedProfit,
          status,
        })
        .run();

      // Update staleness tracking on the variant
      db.update(variants)
        .set({
          lastPriceCheck: new Date().toISOString(),
          lastMarketPrice: change.marketPrice,
        })
        .where(eq(variants.shopifyVariantId, change.variantId))
        .run();
    }

    // Also update staleness for no-change items (they were validated too)
    const now = new Date().toISOString();
    for (const item of noChange) {
      db.update(variants)
        .set({
          lastPriceCheck: now,
          lastMarketPrice: item.marketPrice,
        })
        .where(eq(variants.shopifyVariantId, item.variantId))
        .run();
    }

    return NextResponse.json({
      success: true,
      runId: run.id,
      summary: {
        totalMatched: matches.length,
        unmatched: unmatched.length,
        autoApplied: successCount,
        failedToApply: failCount,
        needsReview: needsReview.length,
        rejected: rejected.length,
        skippedProfit: skippedProfit.length,
        noChange: noChange.length,
        netAdjustment: Math.round(netAdjustment * 100) / 100,
        adCostPerOrder: Math.round(adCostPerOrder * 100) / 100,
      },
    });
  } catch (error) {
    console.error("Automated price sync failed:", error);
    return NextResponse.json(
      { error: "Automated price sync failed" },
      { status: 500 }
    );
  }
}
