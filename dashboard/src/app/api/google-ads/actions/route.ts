import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { googleAdsActions } from "@db/schema";
import { desc } from "drizzle-orm";

export async function GET() {
  try {
    const actions = db
      .select()
      .from(googleAdsActions)
      .orderBy(desc(googleAdsActions.executedAt))
      .limit(100)
      .all()
      .map((a) => ({ ...a, success: Boolean(a.success) }));

    return NextResponse.json({ actions });
  } catch (error) {
    console.error("Failed to fetch ads actions:", error);
    return NextResponse.json({ actions: [] });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { actionType, targetEntityType, targetEntityId, targetEntityName, reason } = body;

    if (!actionType || !targetEntityId || !targetEntityName) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const action = db
      .insert(googleAdsActions)
      .values({
        actionType,
        targetEntityType: targetEntityType ?? "unknown",
        targetEntityId,
        targetEntityName,
        reason: reason ?? "Manual action",
        executedAt: new Date().toISOString(),
        success: 1,
      })
      .returning()
      .get();

    return NextResponse.json({ action: { ...action, success: Boolean(action.success) } });
  } catch (error) {
    console.error("Failed to execute ad action:", error);
    return NextResponse.json({ error: "Failed to execute action" }, { status: 500 });
  }
}
