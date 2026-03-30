import { NextResponse } from "next/server";
import { db } from "@db/index";
import { googleAdsPerformance, googleAdsSearchTerms, googleAdsActions } from "@db/schema";
import { gte, sql, eq, and } from "drizzle-orm";
import { getGoogleAdsConfig } from "@/lib/config";
import { isGoogleAdsConfigured, addNegativeKeyword } from "@/lib/google-ads";
import { isCircuitBreakerTripped, tripCircuitBreaker, HARD_LIMITS } from "@/lib/safety";

/**
 * POST /api/google-ads/optimize — Run automated bid optimization
 */
export async function POST() {
  try {
    // Check circuit breaker
    const breaker = isCircuitBreakerTripped("google_ads");
    if (breaker.tripped) {
      return NextResponse.json(
        { error: `Google Ads circuit breaker is tripped: ${breaker.reason}` },
        { status: 423 }
      );
    }

    const config = getGoogleAdsConfig();
    const now = new Date().toISOString();
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split("T")[0];
    const actions: Array<{ type: string; entity: string; reason: string }> = [];

    // Get product-level performance (30 days aggregated)
    const products = db
      .select({
        entityId: googleAdsPerformance.entityId,
        entityName: googleAdsPerformance.entityName,
        clicks: sql<number>`sum(clicks)`,
        cost: sql<number>`sum(cost)`,
        conversions: sql<number>`sum(conversions)`,
        conversionValue: sql<number>`sum(conversion_value)`,
      })
      .from(googleAdsPerformance)
      .where(
        and(
          eq(googleAdsPerformance.entityType, "product"),
          gte(googleAdsPerformance.date, thirtyDaysAgo)
        )
      )
      .groupBy(googleAdsPerformance.entityId)
      .all();

    let pauseCount = 0;

    for (const product of products) {
      const roas = product.cost > 0 ? (product.conversionValue / product.cost) * 100 : 0;

      // Rule 1: Pause products with 50+ clicks and 0 conversions
      if (product.clicks >= 50 && product.conversions === 0) {
        if (pauseCount < HARD_LIMITS.MAX_PRODUCTS_PAUSED_PER_RUN) {
          db.insert(googleAdsActions).values({
            actionType: "pause_product",
            targetEntityType: "product",
            targetEntityId: product.entityId,
            targetEntityName: product.entityName,
            oldValue: "enabled",
            newValue: "paused",
            reason: `${product.clicks} clicks, 0 conversions, $${product.cost.toFixed(2)} spent`,
            executedAt: now,
            success: 1,
          }).run();

          pauseCount++;
          actions.push({
            type: "pause_product",
            entity: product.entityName,
            reason: `${product.clicks} clicks, 0 conversions`,
          });
        }
      }

      // Rule 2: Flag high-ROAS products for bid increase
      if (roas > 700 && product.conversions >= 2) {
        db.insert(googleAdsActions).values({
          actionType: "bid_increase",
          targetEntityType: "product",
          targetEntityId: product.entityId,
          targetEntityName: product.entityName,
          oldValue: null,
          newValue: "+20% bid recommended",
          reason: `ROAS ${Math.round(roas)}% with ${product.conversions} conversions`,
          executedAt: now,
          success: 1,
        }).run();

        actions.push({
          type: "bid_increase",
          entity: product.entityName,
          reason: `ROAS ${Math.round(roas)}%`,
        });
      }

      // Rule 3: Flag low-ROAS products for bid decrease
      if (roas < 300 && roas > 0 && product.clicks >= 30) {
        db.insert(googleAdsActions).values({
          actionType: "bid_decrease",
          targetEntityType: "product",
          targetEntityId: product.entityId,
          targetEntityName: product.entityName,
          oldValue: null,
          newValue: "-20% bid recommended",
          reason: `ROAS ${Math.round(roas)}% with ${product.clicks} clicks`,
          executedAt: now,
          success: 1,
        }).run();

        actions.push({
          type: "bid_decrease",
          entity: product.entityName,
          reason: `Low ROAS ${Math.round(roas)}%`,
        });
      }
    }

    // Rule 4: Find negative keyword candidates from search terms
    const searchTerms = db
      .select({
        searchTerm: googleAdsSearchTerms.searchTerm,
        campaignId: googleAdsSearchTerms.campaignId,
        clicks: sql<number>`sum(clicks)`,
        cost: sql<number>`sum(cost)`,
        conversions: sql<number>`sum(conversions)`,
      })
      .from(googleAdsSearchTerms)
      .where(
        and(
          eq(googleAdsSearchTerms.isNegative, 0),
          gte(googleAdsSearchTerms.date, thirtyDaysAgo)
        )
      )
      .groupBy(googleAdsSearchTerms.searchTerm)
      .all();

    let negativeCount = 0;

    for (const term of searchTerms) {
      if (term.clicks >= 5 && term.conversions === 0 && negativeCount < HARD_LIMITS.MAX_NEGATIVE_KEYWORDS_PER_WEEK) {
        // Add as negative keyword if Google Ads is configured
        let success = true;
        if (isGoogleAdsConfigured(config)) {
          const result = await addNegativeKeyword(config, term.campaignId, term.searchTerm);
          success = result.success;
        }

        db.insert(googleAdsActions).values({
          actionType: "add_negative_keyword",
          targetEntityType: "search_term",
          targetEntityId: term.campaignId,
          targetEntityName: term.searchTerm,
          oldValue: null,
          newValue: "negative_broad",
          reason: `${term.clicks} clicks, 0 conversions, $${term.cost.toFixed(2)} wasted`,
          executedAt: now,
          success: success ? 1 : 0,
        }).run();

        if (success) {
          // Mark as negative in search terms table
          db.update(googleAdsSearchTerms)
            .set({ isNegative: 1 })
            .where(eq(googleAdsSearchTerms.searchTerm, term.searchTerm))
            .run();
        }

        negativeCount++;
        actions.push({
          type: "add_negative_keyword",
          entity: term.searchTerm,
          reason: `${term.clicks} clicks, 0 conversions`,
        });
      }
    }

    // Circuit breaker: check if overall ROAS is dangerously low
    const overallPerf = db
      .select({
        totalCost: sql<number>`sum(cost)`,
        totalValue: sql<number>`sum(conversion_value)`,
      })
      .from(googleAdsPerformance)
      .where(gte(googleAdsPerformance.date, new Date(Date.now() - 3 * 86400000).toISOString().split("T")[0]))
      .get();

    if (overallPerf && overallPerf.totalCost > 0) {
      const recentRoas = (overallPerf.totalValue / overallPerf.totalCost) * 100;
      if (recentRoas < 300) {
        tripCircuitBreaker(
          "google_ads",
          `3-day ROAS dropped to ${Math.round(recentRoas)}% (below 300% threshold)`
        );
      }
    }

    return NextResponse.json({
      success: true,
      actions,
      summary: {
        productsPaused: pauseCount,
        negativeKeywordsAdded: negativeCount,
        bidRecommendations: actions.filter((a) => a.type.includes("bid")).length,
        totalActions: actions.length,
      },
    });
  } catch (error) {
    console.error("Google Ads optimization failed:", error);
    return NextResponse.json({ error: "Failed to run optimization" }, { status: 500 });
  }
}
