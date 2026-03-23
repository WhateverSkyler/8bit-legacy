import { NextRequest, NextResponse } from "next/server";
import { getEbayConfig } from "@/lib/config";
import { searchEbay, getEbaySearchUrl } from "@/lib/ebay";

// GET /api/ebay/search?q=query&maxPrice=30&condition=USED
export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const query = params.get("q");
  const maxPrice = params.get("maxPrice")
    ? parseFloat(params.get("maxPrice")!)
    : undefined;
  const condition = (params.get("condition") ?? "USED") as
    | "USED"
    | "NEW"
    | "ANY";

  if (!query) {
    return NextResponse.json(
      { error: "Missing required parameter: q" },
      { status: 400 }
    );
  }

  const config = getEbayConfig();

  if (!config.appId) {
    // Return fallback URL when eBay API is not configured
    return NextResponse.json({
      query,
      results: [],
      isFallback: true,
      fallbackUrl: getEbaySearchUrl(query, maxPrice),
    });
  }

  try {
    const result = await searchEbay(query, config.appId, {
      maxPrice,
      condition,
    });
    return NextResponse.json(result);
  } catch (error) {
    console.error("eBay search error:", error);
    return NextResponse.json(
      {
        query,
        results: [],
        isFallback: true,
        fallbackUrl: getEbaySearchUrl(query, maxPrice),
        error: "eBay API error — use fallback URL",
      },
      { status: 200 }
    );
  }
}
