import { NextResponse } from "next/server";
import { getShopifyConfig } from "@/lib/config";
import { fetchUnfulfilledOrders } from "@/lib/shopify";
import { validateOrderPrices } from "@/lib/order-validator";

/**
 * POST /api/fulfillment/validate
 *
 * Validate all unfulfilled order prices against current market data.
 * Creates alerts for items that would be sold at a loss or thin margin.
 */
export async function POST() {
  try {
    const config = getShopifyConfig();
    if (!config.storeUrl || !config.accessToken) {
      return NextResponse.json({ error: "Shopify not configured" }, { status: 400 });
    }

    const orders = await fetchUnfulfilledOrders(config);
    const validation = validateOrderPrices(orders);

    return NextResponse.json({
      success: true,
      summary: {
        ordersChecked: orders.length,
        itemsValidated: validation.validated,
        losses: validation.losses,
        thinMargins: validation.thinMargins,
        alertsCreated: validation.alertsCreated,
      },
      issues: validation.results.filter((r) => r.status !== "profitable"),
    });
  } catch (error) {
    console.error("Order validation failed:", error);
    return NextResponse.json({ error: "Order validation failed" }, { status: 500 });
  }
}
