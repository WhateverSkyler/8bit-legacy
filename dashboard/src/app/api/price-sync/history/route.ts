import { NextResponse } from "next/server";

// GET /api/price-sync/history — past sync runs
// TODO: Read from SQLite when Phase 3 is complete
export async function GET() {
  return NextResponse.json({
    runs: [
      { id: 1, timestamp: "2026-03-20T10:00:00Z", totalItems: 65, changesApplied: 12, belowProfit: 3, unmatched: 5, netAdjustment: 24.50 },
      { id: 2, timestamp: "2026-03-13T10:00:00Z", totalItems: 62, changesApplied: 8, belowProfit: 4, unmatched: 5, netAdjustment: -12.75 },
      { id: 3, timestamp: "2026-03-06T10:00:00Z", totalItems: 60, changesApplied: 15, belowProfit: 2, unmatched: 6, netAdjustment: 38.20 },
    ],
  });
}
