import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { googleAdsPerformance } from "@db/schema";
import { desc, eq, gte, sql } from "drizzle-orm";

const SAMPLE_PERFORMANCE = {
  summary: {
    totalSpend: 342.50,
    totalRevenue: 1890.20,
    roas: 552,
    avgCpc: 0.28,
    totalClicks: 1223,
    totalConversions: 42,
  },
  daily: Array.from({ length: 30 }, (_, i) => {
    const d = new Date(Date.now() - (29 - i) * 86400000);
    const spend = 8 + Math.random() * 12;
    const rev = spend * (4 + Math.random() * 3);
    return {
      date: d.toISOString().split("T")[0],
      spend: Math.round(spend * 100) / 100,
      revenue: Math.round(rev * 100) / 100,
    };
  }),
  campaigns: [],
  products: [],
};

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const entityType = searchParams.get("entityType");
    const days = parseInt(searchParams.get("days") ?? "30");

    const startDate = new Date(Date.now() - days * 86400000).toISOString().split("T")[0];

    // Check if we have data
    const dataCount = db
      .select({ count: sql<number>`count(*)` })
      .from(googleAdsPerformance)
      .get();

    if (!dataCount || dataCount.count === 0) {
      return NextResponse.json({ ...SAMPLE_PERFORMANCE, source: "sample" });
    }

    // Aggregate summary
    const summary = db
      .select({
        totalSpend: sql<number>`sum(cost)`,
        totalRevenue: sql<number>`sum(conversion_value)`,
        totalClicks: sql<number>`sum(clicks)`,
        totalConversions: sql<number>`sum(conversions)`,
        totalImpressions: sql<number>`sum(impressions)`,
      })
      .from(googleAdsPerformance)
      .where(gte(googleAdsPerformance.date, startDate))
      .get();

    const totalSpend = summary?.totalSpend ?? 0;
    const totalRevenue = summary?.totalRevenue ?? 0;

    // Daily breakdown
    const daily = db
      .select({
        date: googleAdsPerformance.date,
        spend: sql<number>`sum(cost)`,
        revenue: sql<number>`sum(conversion_value)`,
      })
      .from(googleAdsPerformance)
      .where(gte(googleAdsPerformance.date, startDate))
      .groupBy(googleAdsPerformance.date)
      .orderBy(googleAdsPerformance.date)
      .all();

    // Entity-level data
    let entities: Array<Record<string, unknown>> = [];
    if (entityType) {
      entities = db
        .select({
          entityId: googleAdsPerformance.entityId,
          entityName: googleAdsPerformance.entityName,
          impressions: sql<number>`sum(impressions)`,
          clicks: sql<number>`sum(clicks)`,
          cost: sql<number>`sum(cost)`,
          conversions: sql<number>`sum(conversions)`,
          conversionValue: sql<number>`sum(conversion_value)`,
        })
        .from(googleAdsPerformance)
        .where(eq(googleAdsPerformance.entityType, entityType))
        .groupBy(googleAdsPerformance.entityId)
        .orderBy(desc(sql`sum(clicks)`))
        .limit(100)
        .all()
        .map((e) => ({
          ...e,
          roas: e.cost > 0 ? Math.round((e.conversionValue / e.cost) * 100) / 100 : 0,
          cpc: e.clicks > 0 ? Math.round((e.cost / e.clicks) * 100) / 100 : 0,
        }));
    }

    return NextResponse.json({
      summary: {
        totalSpend: Math.round(totalSpend * 100) / 100,
        totalRevenue: Math.round(totalRevenue * 100) / 100,
        roas: totalSpend > 0 ? Math.round((totalRevenue / totalSpend) * 100) : 0,
        avgCpc: (summary?.totalClicks ?? 0) > 0
          ? Math.round((totalSpend / (summary?.totalClicks ?? 1)) * 100) / 100
          : 0,
        totalClicks: summary?.totalClicks ?? 0,
        totalConversions: summary?.totalConversions ?? 0,
      },
      daily,
      entities,
      source: "database",
    });
  } catch (error) {
    console.error("Failed to fetch ads performance:", error);
    return NextResponse.json({ ...SAMPLE_PERFORMANCE, source: "sample" });
  }
}
