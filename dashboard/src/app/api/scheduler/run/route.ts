import { NextRequest, NextResponse } from "next/server";
import { runJobNow } from "@/lib/scheduler";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { jobName } = body;

    if (!jobName || typeof jobName !== "string") {
      return NextResponse.json(
        { error: "Missing or invalid jobName" },
        { status: 400 }
      );
    }

    const result = await runJobNow(jobName);

    return NextResponse.json(result);
  } catch (error) {
    console.error("Failed to run job:", error);
    return NextResponse.json(
      { error: "Failed to run job" },
      { status: 500 }
    );
  }
}
