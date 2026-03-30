import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { fulfillmentTasks } from "@db/schema";
import { eq } from "drizzle-orm";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const taskId = parseInt(id);
    if (isNaN(taskId)) {
      return NextResponse.json({ error: "Invalid task ID" }, { status: 400 });
    }

    const existing = db
      .select()
      .from(fulfillmentTasks)
      .where(eq(fulfillmentTasks.id, taskId))
      .get();

    if (!existing) {
      return NextResponse.json({ error: "Task not found" }, { status: 404 });
    }

    const body = await request.json();
    const updates: Record<string, unknown> = {};

    // Handle status transitions
    if (body.status) {
      const validTransitions: Record<string, string[]> = {
        pending: ["ordered_on_ebay", "cancelled"],
        ordered_on_ebay: ["awaiting_shipment", "shipped", "cancelled"],
        awaiting_shipment: ["shipped", "cancelled"],
        shipped: ["delivered", "cancelled"],
        delivered: ["fulfilled"],
        fulfilled: [],
        cancelled: ["pending"],
      };

      const allowed = validTransitions[existing.status] ?? [];
      if (!allowed.includes(body.status)) {
        return NextResponse.json(
          { error: `Cannot transition from "${existing.status}" to "${body.status}"` },
          { status: 400 }
        );
      }

      updates.status = body.status;

      // Set timestamps based on status
      if (body.status === "ordered_on_ebay") {
        updates.orderedAt = new Date().toISOString();
      } else if (body.status === "shipped") {
        updates.shippedAt = new Date().toISOString();
      } else if (body.status === "delivered") {
        updates.deliveredAt = new Date().toISOString();
      } else if (body.status === "fulfilled") {
        updates.fulfilledAt = new Date().toISOString();
      }
    }

    // Update eBay details
    if (body.ebayOrderId !== undefined) updates.ebayOrderId = body.ebayOrderId;
    if (body.ebayListingUrl !== undefined) updates.ebayListingUrl = body.ebayListingUrl;
    if (body.ebayPurchasePrice !== undefined) updates.ebayPurchasePrice = body.ebayPurchasePrice;
    if (body.ebaySellerName !== undefined) updates.ebaySellerName = body.ebaySellerName;

    // Update tracking
    if (body.trackingNumber !== undefined) updates.trackingNumber = body.trackingNumber;
    if (body.trackingCarrier !== undefined) updates.trackingCarrier = body.trackingCarrier;

    // Update notes
    if (body.notes !== undefined) updates.notes = body.notes;

    if (Object.keys(updates).length === 0) {
      return NextResponse.json({ error: "No updates provided" }, { status: 400 });
    }

    db.update(fulfillmentTasks)
      .set(updates)
      .where(eq(fulfillmentTasks.id, taskId))
      .run();

    const updated = db
      .select()
      .from(fulfillmentTasks)
      .where(eq(fulfillmentTasks.id, taskId))
      .get();

    return NextResponse.json({ task: updated });
  } catch (error) {
    console.error("Failed to update fulfillment task:", error);
    return NextResponse.json({ error: "Failed to update fulfillment task" }, { status: 500 });
  }
}
