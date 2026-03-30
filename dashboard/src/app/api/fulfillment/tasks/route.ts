import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { fulfillmentTasks } from "@db/schema";
import { desc, eq } from "drizzle-orm";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status");

    let query = db.select().from(fulfillmentTasks).orderBy(desc(fulfillmentTasks.createdAt));

    if (status) {
      query = query.where(eq(fulfillmentTasks.status, status)) as typeof query;
    }

    const tasks = query.all().map((t) => ({
      ...t,
      // Compute profit if we have both prices
      profit:
        t.ebayPurchasePrice != null
          ? Math.round(
              (t.lineItemPrice -
                t.ebayPurchasePrice -
                (t.lineItemPrice * 0.029 + 0.3)) *
                100
            ) / 100
          : null,
    }));

    return NextResponse.json({ tasks });
  } catch (error) {
    console.error("Failed to fetch fulfillment tasks:", error);
    return NextResponse.json({ error: "Failed to fetch fulfillment tasks" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      shopifyOrderId,
      shopifyOrderNumber,
      lineItemTitle,
      lineItemSku,
      lineItemPrice,
      lineItemQuantity,
      lineItemImageUrl,
      customerName,
      customerCity,
    } = body;

    if (!shopifyOrderId || !lineItemTitle || !customerName) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const task = db
      .insert(fulfillmentTasks)
      .values({
        shopifyOrderId,
        shopifyOrderNumber: shopifyOrderNumber ?? "",
        lineItemTitle,
        lineItemSku: lineItemSku ?? "",
        lineItemPrice: lineItemPrice ?? 0,
        lineItemQuantity: lineItemQuantity ?? 1,
        lineItemImageUrl: lineItemImageUrl ?? null,
        status: "pending",
        customerName,
        customerCity: customerCity ?? "",
        createdAt: new Date().toISOString(),
      })
      .returning()
      .get();

    return NextResponse.json({ task });
  } catch (error) {
    console.error("Failed to create fulfillment task:", error);
    return NextResponse.json({ error: "Failed to create fulfillment task" }, { status: 500 });
  }
}
