import { NextResponse } from "next/server";
import { getAdsSafetyStatus } from "@/lib/safety";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const status = getAdsSafetyStatus();
    return NextResponse.json(status);
  } catch (error) {
    console.error("Failed to compute ads safety status:", error);
    return NextResponse.json(
      { error: "Failed to compute ads safety status" },
      { status: 500 }
    );
  }
}
