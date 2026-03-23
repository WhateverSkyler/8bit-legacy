import { NextRequest, NextResponse } from "next/server";
import { getShopifyConfig } from "@/lib/config";
import { fetchUnfulfilledOrders } from "@/lib/shopify";

// GET /api/shopify/orders — fetch orders from Shopify
export async function GET(request: NextRequest) {
  const config = getShopifyConfig();

  if (!config.storeUrl || !config.accessToken) {
    return NextResponse.json({
      orders: SAMPLE_ORDERS,
      source: "sample",
    });
  }

  try {
    const orders = await fetchUnfulfilledOrders(config);
    return NextResponse.json({ orders, source: "shopify" });
  } catch (error) {
    console.error("Failed to fetch orders:", error);
    return NextResponse.json(
      { error: "Failed to fetch orders from Shopify" },
      { status: 500 }
    );
  }
}

const SAMPLE_ORDERS = [
  { id: "gid://o1", orderNumber: "#1042", createdAt: "2026-03-23T14:00:00Z", status: "unfulfilled", customerName: "Alex M.", customerCity: "Atlanta, GA 30301", totalPrice: 34.99, lineItems: [{ title: "Super Mario Bros 3", quantity: 1, price: 34.99, sku: "SMB3-NES", imageUrl: null }] },
  { id: "gid://o2", orderNumber: "#1041", createdAt: "2026-03-23T09:00:00Z", status: "unfulfilled", customerName: "Sarah K.", customerCity: "Portland, OR 97201", totalPrice: 49.99, lineItems: [{ title: "Pokemon Red", quantity: 1, price: 49.99, sku: "PKR-GB", imageUrl: null }] },
  { id: "gid://o3", orderNumber: "#1040", createdAt: "2026-03-22T16:00:00Z", status: "fulfilled", customerName: "Mike R.", customerCity: "Chicago, IL 60601", totalPrice: 29.99, lineItems: [{ title: "GoldenEye 007", quantity: 1, price: 29.99, sku: "GE007-N64", imageUrl: null }] },
  { id: "gid://o4", orderNumber: "#1039", createdAt: "2026-03-22T11:00:00Z", status: "fulfilled", customerName: "Lisa P.", customerCity: "Denver, CO 80201", totalPrice: 14.99, lineItems: [{ title: "Sonic the Hedgehog 2", quantity: 1, price: 14.99, sku: "SH2-GEN", imageUrl: null }] },
];
