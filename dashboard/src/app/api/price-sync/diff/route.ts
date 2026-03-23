import { NextRequest, NextResponse } from "next/server";
import { getPricingConfig, getShopifyConfig } from "@/lib/config";
import { matchProducts, generateDiff } from "@/lib/matching";
import { fetchAllProducts } from "@/lib/shopify";
import type { PriceChartingItem } from "@/types/product";

// POST /api/price-sync/diff — generate a diff report
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const pcItems: PriceChartingItem[] = body.pcItems;
    const minChange: number = body.minChange ?? 0.5;

    if (!pcItems || pcItems.length === 0) {
      return NextResponse.json(
        { error: "No PriceCharting items provided" },
        { status: 400 }
      );
    }

    const shopifyConfig = getShopifyConfig();
    const pricingConfig = getPricingConfig();

    // Fetch Shopify products (or use sample data)
    let shopifyProducts;
    if (shopifyConfig.storeUrl && shopifyConfig.accessToken) {
      shopifyProducts = await fetchAllProducts(shopifyConfig);
    } else {
      // Sample products for demo
      shopifyProducts = SAMPLE_SHOPIFY_PRODUCTS;
    }

    // Match and diff
    const { matches, unmatched } = matchProducts(pcItems, shopifyProducts);
    const { changes, skippedProfit, noChange } = generateDiff(
      matches,
      pricingConfig,
      minChange
    );

    return NextResponse.json({
      changes,
      skippedProfit,
      noChange,
      unmatched,
      summary: {
        totalPcItems: pcItems.length,
        matched: matches.length,
        changesNeeded: changes.length,
        belowProfit: skippedProfit.length,
        noChangeNeeded: noChange.length,
        unmatchedCount: unmatched.length,
      },
    });
  } catch (error) {
    console.error("Diff generation error:", error);
    return NextResponse.json(
      { error: "Failed to generate diff report" },
      { status: 500 }
    );
  }
}

const SAMPLE_SHOPIFY_PRODUCTS = [
  { productId: "gid://1", productTitle: "Super Mario Bros 3", productHandle: "super-mario-bros-3", productTags: ["NES"], variantId: "gid://v1", variantTitle: "Default", sku: "SMB3-NES", currentPrice: 32.99, barcode: "" },
  { productId: "gid://2", productTitle: "The Legend of Zelda: A Link to the Past", productHandle: "zelda-lttp", productTags: ["SNES"], variantId: "gid://v2", variantTitle: "Default", sku: "ZLTP-SNES", currentPrice: 42.99, barcode: "" },
  { productId: "gid://5", productTitle: "Pokemon Red", productHandle: "pokemon-red", productTags: ["Game Boy"], variantId: "gid://v5", variantTitle: "Default", sku: "PKR-GB", currentPrice: 47.99, barcode: "" },
];
