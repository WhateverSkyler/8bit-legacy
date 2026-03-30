import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { fulfillmentAlerts } from "@db/schema";
import { desc, eq } from "drizzle-orm";

export async function GET() {
  try {
    const alerts = db
      .select()
      .from(fulfillmentAlerts)
      .where(eq(fulfillmentAlerts.acknowledged, 0))
      .orderBy(desc(fulfillmentAlerts.createdAt))
      .all()
      .map((a) => ({ ...a, acknowledged: Boolean(a.acknowledged) }));

    return NextResponse.json({ alerts });
  } catch (error) {
    console.error("Failed to fetch fulfillment alerts:", error);
    return NextResponse.json({ error: "Failed to fetch alerts" }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id } = body;

    if (!id) {
      return NextResponse.json({ error: "Missing alert ID" }, { status: 400 });
    }

    db.update(fulfillmentAlerts)
      .set({ acknowledged: 1 })
      .where(eq(fulfillmentAlerts.id, id))
      .run();

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to acknowledge alert:", error);
    return NextResponse.json({ error: "Failed to acknowledge alert" }, { status: 500 });
  }
}
