import { NextRequest, NextResponse } from "next/server";
import { getShopifyConfig } from "@/lib/config";
import { updateVariantPrice } from "@/lib/shopify";

// POST /api/price-sync/apply — apply price changes to Shopify
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const changes: { variantId: string; newPrice: number }[] = body.changes;

    if (!changes || changes.length === 0) {
      return NextResponse.json(
        { error: "No changes to apply" },
        { status: 400 }
      );
    }

    const config = getShopifyConfig();

    if (!config.storeUrl || !config.accessToken) {
      return NextResponse.json(
        { error: "Shopify not configured. Set API credentials in Settings." },
        { status: 400 }
      );
    }

    const results = { success: 0, failed: 0, errors: [] as string[] };

    for (const change of changes) {
      const result = await updateVariantPrice(
        config,
        change.variantId,
        change.newPrice
      );

      if (result.success) {
        results.success++;
      } else {
        results.failed++;
        results.errors.push(
          `${change.variantId}: ${result.errors?.join(", ")}`
        );
      }

      // Rate limiting: ~4 requests/sec
      await new Promise((r) => setTimeout(r, 250));
    }

    return NextResponse.json(results);
  } catch (error) {
    console.error("Price apply error:", error);
    return NextResponse.json(
      { error: "Failed to apply price changes" },
      { status: 500 }
    );
  }
}
