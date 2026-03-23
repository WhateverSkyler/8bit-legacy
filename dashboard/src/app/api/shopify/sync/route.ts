import { NextResponse } from "next/server";
import { getShopifyConfig } from "@/lib/config";
import { fetchAllProducts, fetchUnfulfilledOrders } from "@/lib/shopify";

// POST /api/shopify/sync — sync all data from Shopify
// TODO: When Phase 3 (SQLite) is complete, upsert into local DB
export async function POST() {
  const config = getShopifyConfig();

  if (!config.storeUrl || !config.accessToken) {
    return NextResponse.json(
      { error: "Shopify not configured" },
      { status: 400 }
    );
  }

  try {
    const startTime = Date.now();

    const [products, orders] = await Promise.all([
      fetchAllProducts(config),
      fetchUnfulfilledOrders(config),
    ]);

    const duration = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      products: products.length,
      orders: orders.length,
      durationMs: duration,
    });
  } catch (error) {
    console.error("Shopify sync error:", error);
    return NextResponse.json(
      { error: "Shopify sync failed" },
      { status: 500 }
    );
  }
}
