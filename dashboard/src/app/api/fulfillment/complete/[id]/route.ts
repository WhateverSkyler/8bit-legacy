import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { fulfillmentTasks } from "@db/schema";
import { eq } from "drizzle-orm";
import { getShopifyConfig } from "@/lib/config";
import { fulfillOrder } from "@/lib/shopify";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const taskId = parseInt(id);
    if (isNaN(taskId)) {
      return NextResponse.json({ error: "Invalid task ID" }, { status: 400 });
    }

    const task = db
      .select()
      .from(fulfillmentTasks)
      .where(eq(fulfillmentTasks.id, taskId))
      .get();

    if (!task) {
      return NextResponse.json({ error: "Task not found" }, { status: 404 });
    }

    if (task.status !== "delivered" && task.status !== "shipped") {
      return NextResponse.json(
        { error: `Cannot fulfill task with status "${task.status}". Must be "delivered" or "shipped".` },
        { status: 400 }
      );
    }

    const config = getShopifyConfig();
    let shopifyFulfilled = false;

    if (config.storeUrl && config.accessToken) {
      // Call Shopify to mark order as fulfilled
      const result = await fulfillOrder(
        config,
        task.shopifyOrderId,
        task.trackingNumber ?? "",
        task.trackingCarrier ?? ""
      );
      shopifyFulfilled = result.success;

      if (!result.success) {
        console.error("Shopify fulfillment errors:", result.errors);
      }
    } else {
      // Demo mode — just update local DB
      shopifyFulfilled = true;
      console.log(`[Demo] Would fulfill Shopify order ${task.shopifyOrderId} with tracking ${task.trackingNumber}`);
    }

    // Update task status
    db.update(fulfillmentTasks)
      .set({
        status: "fulfilled",
        fulfilledAt: new Date().toISOString(),
      })
      .where(eq(fulfillmentTasks.id, taskId))
      .run();

    return NextResponse.json({
      success: true,
      shopifyFulfilled,
      task: db.select().from(fulfillmentTasks).where(eq(fulfillmentTasks.id, taskId)).get(),
    });
  } catch (error) {
    console.error("Failed to complete fulfillment:", error);
    return NextResponse.json({ error: "Failed to complete fulfillment" }, { status: 500 });
  }
}
