import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { googleAdsPerformance } from "@db/schema";
import { gte, sql } from "drizzle-orm";
import { getAdsSafetyStatus } from "@/lib/safety";

export const dynamic = "force-dynamic";

/**
 * Public token-auth read-only ads snapshot.
 *
 * Used by the recurring Claude Code routine to pull live performance data
 * without requiring Google Ads API credentials in the agent environment.
 *
 * Auth: requires `?token=<ADS_SNAPSHOT_TOKEN>` matching env var.
 *
 * Returns: last 30 days of daily perf, last 7 days summary, current safety
 * status, and 3-day rolling totals.
 */
export async function GET(req: NextRequest) {
  const tokenParam = req.nextUrl.searchParams.get("token");
  const expected = process.env.ADS_SNAPSHOT_TOKEN;
  if (!expected) {
    return NextResponse.json({ error: "Endpoint not configured" }, { status: 503 });
  }
  if (!tokenParam || tokenParam !== expected) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split("T")[0];
    const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString().split("T")[0];

    const dailyRows = db
      .select({
        date: googleAdsPerformance.date,
        cost: sql<number>`coalesce(sum(cost), 0)`,
        clicks: sql<number>`coalesce(sum(clicks), 0)`,
        impressions: sql<number>`coalesce(sum(impressions), 0)`,
        conversions: sql<number>`coalesce(sum(conversions), 0)`,
        conversionValue: sql<number>`coalesce(sum(conversion_value), 0)`,
      })
      .from(googleAdsPerformance)
      .where(gte(googleAdsPerformance.date, thirtyDaysAgo))
      .groupBy(googleAdsPerformance.date)
      .orderBy(googleAdsPerformance.date)
      .all();

    const sevenDay = dailyRows.filter(r => r.date >= sevenDaysAgo);
    const sum7 = sevenDay.reduce(
      (acc, r) => ({
        cost: acc.cost + Number(r.cost ?? 0),
        clicks: acc.clicks + Number(r.clicks ?? 0),
        impressions: acc.impressions + Number(r.impressions ?? 0),
        conversions: acc.conversions + Number(r.conversions ?? 0),
        conversionValue: acc.conversionValue + Number(r.conversionValue ?? 0),
      }),
      { cost: 0, clicks: 0, impressions: 0, conversions: 0, conversionValue: 0 }
    );

    const safety = getAdsSafetyStatus();

    return NextResponse.json({
      generatedAt: new Date().toISOString(),
      windows: {
        last30DaysDaily: dailyRows.map(r => ({
          date: r.date,
          cost: Number(r.cost ?? 0),
          clicks: Number(r.clicks ?? 0),
          impressions: Number(r.impressions ?? 0),
          conversions: Number(r.conversions ?? 0),
          conversionValue: Number(r.conversionValue ?? 0),
          ctr: r.impressions ? (Number(r.clicks) / Number(r.impressions)) * 100 : 0,
          cvr: r.clicks ? (Number(r.conversions) / Number(r.clicks)) * 100 : 0,
          cpc: r.clicks ? Number(r.cost) / Number(r.clicks) : 0,
          roas: r.cost ? (Number(r.conversionValue) / Number(r.cost)) * 100 : 0,
        })),
        last7DaysSummary: {
          ...sum7,
          ctr: sum7.impressions ? (sum7.clicks / sum7.impressions) * 100 : 0,
          cvr: sum7.clicks ? (sum7.conversions / sum7.clicks) * 100 : 0,
          cpc: sum7.clicks ? sum7.cost / sum7.clicks : 0,
          roas: sum7.cost ? (sum7.conversionValue / sum7.cost) * 100 : 0,
        },
      },
      safety,
    });
  } catch (error) {
    console.error("ads-snapshot error:", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
