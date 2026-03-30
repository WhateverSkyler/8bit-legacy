import { NextResponse } from "next/server";
import { getSchedulerStatus } from "@/lib/scheduler";
import { getAllCircuitBreakerStatus } from "@/lib/safety";

export async function GET() {
  try {
    const jobs = getSchedulerStatus();
    const circuitBreakers = getAllCircuitBreakerStatus();

    return NextResponse.json({
      jobs,
      circuitBreakers,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Failed to get scheduler status:", error);
    return NextResponse.json(
      { error: "Failed to get scheduler status" },
      { status: 500 }
    );
  }
}
