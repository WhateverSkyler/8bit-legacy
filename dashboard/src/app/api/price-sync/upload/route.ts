import { NextRequest, NextResponse } from "next/server";
import { parsePriceChartingCSV } from "@/lib/csv-parser";

// POST /api/price-sync/upload — parse a PriceCharting CSV
export async function POST(request: NextRequest) {
  try {
    const csvText = await request.text();

    if (!csvText.trim()) {
      return NextResponse.json(
        { error: "Empty CSV file" },
        { status: 400 }
      );
    }

    const items = parsePriceChartingCSV(csvText);

    return NextResponse.json({
      items,
      count: items.length,
    });
  } catch (error) {
    console.error("CSV parse error:", error);
    return NextResponse.json(
      { error: "Failed to parse CSV file" },
      { status: 500 }
    );
  }
}
