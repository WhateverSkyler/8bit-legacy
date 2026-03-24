import { NextResponse } from "next/server";
import { db, schema } from "@db";
import { desc } from "drizzle-orm";

// GET /api/price-sync/history — past sync runs from SQLite
export async function GET() {
  try {
    const runs = db
      .select()
      .from(schema.priceSyncRuns)
      .orderBy(desc(schema.priceSyncRuns.timestamp))
      .limit(20)
      .all();

    if (runs.length === 0) {
      // Return sample data when DB is empty
      return NextResponse.json({
        runs: SAMPLE_RUNS,
        source: "sample",
      });
    }

    return NextResponse.json({ runs, source: "db" });
  } catch {
    // Fallback if DB isn't initialized yet
    return NextResponse.json({
      runs: SAMPLE_RUNS,
      source: "sample",
    });
  }
}

const SAMPLE_RUNS = [
  { id: 1, timestamp: "2026-03-20T10:00:00Z", totalItems: 65, changesApplied: 12, belowProfit: 3, unmatched: 5, netAdjustment: 24.50 },
  { id: 2, timestamp: "2026-03-13T10:00:00Z", totalItems: 62, changesApplied: 8, belowProfit: 4, unmatched: 5, netAdjustment: -12.75 },
  { id: 3, timestamp: "2026-03-06T10:00:00Z", totalItems: 60, changesApplied: 15, belowProfit: 2, unmatched: 6, netAdjustment: 38.20 },
];
