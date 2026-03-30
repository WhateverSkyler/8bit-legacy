import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { automationRuns } from "@db/schema";
import { desc, eq } from "drizzle-orm";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const jobName = searchParams.get("job");
    const limit = Math.min(parseInt(searchParams.get("limit") ?? "20"), 100);

    let query = db
      .select()
      .from(automationRuns)
      .orderBy(desc(automationRuns.startedAt))
      .limit(limit);

    if (jobName) {
      query = query.where(eq(automationRuns.jobName, jobName)) as typeof query;
    }

    const runs = query.all();

    return NextResponse.json({ runs });
  } catch (error) {
    console.error("Failed to fetch automation runs:", error);
    return NextResponse.json(
      { error: "Failed to fetch automation runs" },
      { status: 500 }
    );
  }
}
