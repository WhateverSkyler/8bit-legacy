import { NextRequest, NextResponse } from "next/server";
import { getShopifyConfig } from "@/lib/config";
import { fetchAllProducts } from "@/lib/shopify";

// GET /api/shopify/products — fetch all products from Shopify
export async function GET(request: NextRequest) {
  const config = getShopifyConfig();

  if (!config.storeUrl || !config.accessToken) {
    // Return sample data when Shopify is not configured
    return NextResponse.json({
      products: SAMPLE_PRODUCTS,
      source: "sample",
    });
  }

  try {
    const products = await fetchAllProducts(config);
    return NextResponse.json({ products, source: "shopify" });
  } catch (error) {
    console.error("Failed to fetch products:", error);
    return NextResponse.json(
      { error: "Failed to fetch products from Shopify" },
      { status: 500 }
    );
  }
}

const SAMPLE_PRODUCTS = [
  { productId: "gid://1", productTitle: "Super Mario Bros 3", productHandle: "super-mario-bros-3", productTags: ["NES"], variantId: "gid://v1", variantTitle: "Default", sku: "SMB3-NES", currentPrice: 34.99, barcode: "" },
  { productId: "gid://2", productTitle: "The Legend of Zelda: A Link to the Past", productHandle: "zelda-link-to-the-past", productTags: ["SNES"], variantId: "gid://v2", variantTitle: "Default", sku: "ZLTP-SNES", currentPrice: 44.99, barcode: "" },
  { productId: "gid://3", productTitle: "Sonic the Hedgehog 2", productHandle: "sonic-2", productTags: ["Genesis"], variantId: "gid://v3", variantTitle: "Default", sku: "SH2-GEN", currentPrice: 14.99, barcode: "" },
  { productId: "gid://4", productTitle: "GoldenEye 007", productHandle: "goldeneye-007", productTags: ["N64"], variantId: "gid://v4", variantTitle: "Default", sku: "GE007-N64", currentPrice: 29.99, barcode: "" },
  { productId: "gid://5", productTitle: "Pokemon Red", productHandle: "pokemon-red", productTags: ["Game Boy"], variantId: "gid://v5", variantTitle: "Default", sku: "PKR-GB", currentPrice: 49.99, barcode: "" },
  { productId: "gid://6", productTitle: "Final Fantasy VII", productHandle: "final-fantasy-vii", productTags: ["PlayStation"], variantId: "gid://v6", variantTitle: "Default", sku: "FF7-PS1", currentPrice: 39.99, barcode: "" },
  { productId: "gid://7", productTitle: "Super Smash Bros", productHandle: "super-smash-bros", productTags: ["N64"], variantId: "gid://v7", variantTitle: "Default", sku: "SSB-N64", currentPrice: 39.99, barcode: "" },
  { productId: "gid://8", productTitle: "Mega Man 2", productHandle: "mega-man-2", productTags: ["NES"], variantId: "gid://v8", variantTitle: "Default", sku: "MM2-NES", currentPrice: 24.99, barcode: "" },
];
