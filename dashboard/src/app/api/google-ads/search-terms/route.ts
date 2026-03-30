import { NextResponse } from "next/server";
import { db } from "@db/index";
import { googleAdsSearchTerms } from "@db/schema";
import { gte, sql, desc } from "drizzle-orm";

export async function GET() {
  try {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split("T")[0];

    const terms = db
      .select({
        searchTerm: googleAdsSearchTerms.searchTerm,
        campaignId: googleAdsSearchTerms.campaignId,
        impressions: sql<number>`sum(impressions)`,
        clicks: sql<number>`sum(clicks)`,
        cost: sql<number>`sum(cost)`,
        conversions: sql<number>`sum(conversions)`,
        isNegative: sql<number>`max(is_negative)`,
      })
      .from(googleAdsSearchTerms)
      .where(gte(googleAdsSearchTerms.date, thirtyDaysAgo))
      .groupBy(googleAdsSearchTerms.searchTerm)
      .orderBy(desc(sql`sum(clicks)`))
      .limit(200)
      .all();

    const enriched = terms.map((t) => {
      let suggestedAction: "keep" | "add_negative" | "review" = "review";
      if (t.conversions > 0) {
        suggestedAction = "keep";
      } else if (t.clicks >= 5) {
        suggestedAction = "add_negative";
      }

      return {
        ...t,
        isNegative: Boolean(t.isNegative),
        cost: Math.round(t.cost * 100) / 100,
        suggestedAction,
      };
    });

    return NextResponse.json({ terms: enriched });
  } catch (error) {
    console.error("Failed to fetch search terms:", error);
    return NextResponse.json({ terms: [] });
  }
}
