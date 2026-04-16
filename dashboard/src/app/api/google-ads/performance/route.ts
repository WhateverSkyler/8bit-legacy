import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { googleAdsPerformance } from "@db/schema";
import { desc, eq, gte, sql } from "drizzle-orm";
import { getAllCircuitBreakerStatus } from "@/lib/safety";

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

    // ── Promo credit tracking ──
    const PROMO_CREDIT_TOTAL = 700;
    const PROMO_EXPIRY = "2026-05-31";
    const allTimeSpend = db
      .select({ total: sql<number>`coalesce(sum(cost), 0)` })
      .from(googleAdsPerformance)
      .get();
    const cumulativeSpend = allTimeSpend?.total ?? 0;
    const creditRemaining = Math.max(0, PROMO_CREDIT_TOTAL - cumulativeSpend);
    const daysUntilExpiry = Math.max(0, Math.ceil((new Date(PROMO_EXPIRY).getTime() - Date.now()) / 86400000));
    const requiredDailySpend = daysUntilExpiry > 0 ? creditRemaining / daysUntilExpiry : 0;

    // 7-day average daily spend
    const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString().split("T")[0];
    const recentSpend = db
      .select({ total: sql<number>`coalesce(sum(cost), 0)`, days: sql<number>`count(distinct date)` })
      .from(googleAdsPerformance)
      .where(gte(googleAdsPerformance.date, sevenDaysAgo))
      .get();
    const avgDailySpend = (recentSpend?.days ?? 0) > 0
      ? (recentSpend?.total ?? 0) / (recentSpend?.days ?? 1)
      : 0;

    // ── Rolling 3-day ROAS ──
    const threeDaysAgo = new Date(Date.now() - 3 * 86400000).toISOString().split("T")[0];
    const rolling3d = db
      .select({
        cost: sql<number>`coalesce(sum(cost), 0)`,
        value: sql<number>`coalesce(sum(conversion_value), 0)`,
      })
      .from(googleAdsPerformance)
      .where(gte(googleAdsPerformance.date, threeDaysAgo))
      .get();
    const rolling3dRoas = (rolling3d?.cost ?? 0) > 0
      ? Math.round(((rolling3d?.value ?? 0) / (rolling3d?.cost ?? 1)) * 100)
      : 0;

    // ── Circuit breaker status ──
    const circuitBreakers = getAllCircuitBreakerStatus();

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
        totalImpressions: summary?.totalImpressions ?? 0,
      },
      promoCredit: {
        total: PROMO_CREDIT_TOTAL,
        spent: Math.round(cumulativeSpend * 100) / 100,
        remaining: Math.round(creditRemaining * 100) / 100,
        expiryDate: PROMO_EXPIRY,
        daysUntilExpiry,
        requiredDailySpend: Math.round(requiredDailySpend * 100) / 100,
        avgDailySpend: Math.round(avgDailySpend * 100) / 100,
        onTrack: avgDailySpend >= requiredDailySpend * 0.8,
      },
      rolling3dRoas,
      circuitBreakers,
      daily,
      entities,
      source: "database",
    });
  } catch (error) {
    console.error("Failed to fetch ads performance:", error);
    return NextResponse.json({ ...SAMPLE_PERFORMANCE, source: "sample" });
  }
}
