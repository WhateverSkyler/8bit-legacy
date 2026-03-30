import { NextResponse } from "next/server";
import { db } from "@db/index";
import { googleAdsPerformance, googleAdsSearchTerms } from "@db/schema";
import { getGoogleAdsConfig } from "@/lib/config";
import { isGoogleAdsConfigured, getCampaignPerformance, getProductPerformance, getSearchTermReport } from "@/lib/google-ads";

/**
 * POST /api/google-ads/sync — Pull performance data from Google Ads API
 */
export async function POST() {
  try {
    const config = getGoogleAdsConfig();

    if (!isGoogleAdsConfigured(config)) {
      // Demo mode: insert sample data
      const today = new Date().toISOString().split("T")[0];
      const now = new Date().toISOString();

      const sampleCampaigns = [
        { name: "Shopping - Retro Games", impressions: 2450, clicks: 89, cost: 12.50, conversions: 4, value: 67.80 },
        { name: "Shopping - Pokemon Cards", impressions: 1820, clicks: 64, cost: 8.90, conversions: 3, value: 52.40 },
      ];

      for (const c of sampleCampaigns) {
        db.insert(googleAdsPerformance).values({
          date: today,
          entityType: "campaign",
          entityId: `sample-${c.name.toLowerCase().replace(/\s/g, "-")}`,
          entityName: c.name,
          impressions: c.impressions,
          clicks: c.clicks,
          cost: c.cost,
          conversions: c.conversions,
          conversionValue: c.value,
          roas: c.cost > 0 ? Math.round((c.value / c.cost) * 100) / 100 : 0,
          cpc: c.clicks > 0 ? Math.round((c.cost / c.clicks) * 100) / 100 : 0,
          syncedAt: now,
        }).run();
      }

      return NextResponse.json({ success: true, demo: true, campaigns: sampleCampaigns.length });
    }

    // Real API sync
    const yesterday = new Date(Date.now() - 86400000).toISOString().split("T")[0];
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split("T")[0];
    const now = new Date().toISOString();

    // Sync campaign performance
    const campaigns = await getCampaignPerformance(config, thirtyDaysAgo, yesterday);
    for (const c of campaigns) {
      db.insert(googleAdsPerformance).values({
        date: c.date,
        entityType: "campaign",
        entityId: c.campaignId,
        entityName: c.campaignName,
        impressions: c.impressions,
        clicks: c.clicks,
        cost: c.cost,
        conversions: c.conversions,
        conversionValue: c.conversionValue,
        roas: c.cost > 0 ? Math.round((c.conversionValue / c.cost) * 100) / 100 : 0,
        cpc: c.clicks > 0 ? Math.round((c.cost / c.clicks) * 100) / 100 : 0,
        syncedAt: now,
      }).run();
    }

    // Sync product performance
    const products = await getProductPerformance(config, thirtyDaysAgo, yesterday);
    for (const p of products) {
      db.insert(googleAdsPerformance).values({
        date: p.date,
        entityType: "product",
        entityId: p.productId,
        entityName: p.productTitle,
        impressions: p.impressions,
        clicks: p.clicks,
        cost: p.cost,
        conversions: p.conversions,
        conversionValue: p.conversionValue,
        roas: p.cost > 0 ? Math.round((p.conversionValue / p.cost) * 100) / 100 : 0,
        cpc: p.clicks > 0 ? Math.round((p.cost / p.clicks) * 100) / 100 : 0,
        syncedAt: now,
      }).run();
    }

    // Sync search terms
    const terms = await getSearchTermReport(config, thirtyDaysAgo, yesterday);
    for (const t of terms) {
      db.insert(googleAdsSearchTerms).values({
        date: yesterday,
        searchTerm: t.searchTerm,
        campaignId: t.campaignId,
        impressions: t.impressions,
        clicks: t.clicks,
        cost: t.cost,
        conversions: t.conversions,
        isNegative: 0,
        syncedAt: now,
      }).run();
    }

    return NextResponse.json({
      success: true,
      synced: { campaigns: campaigns.length, products: products.length, searchTerms: terms.length },
    });
  } catch (error) {
    console.error("Google Ads sync failed:", error);
    return NextResponse.json({ error: "Failed to sync Google Ads data" }, { status: 500 });
  }
}
