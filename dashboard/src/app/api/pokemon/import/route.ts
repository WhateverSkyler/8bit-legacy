import { NextRequest, NextResponse } from "next/server";
import { runPython } from "@/lib/python-bridge";

/**
 * POST /api/pokemon/import
 *
 * Trigger a Pokemon card import from the Pokemon TCG API.
 *
 * Body:
 *   sets?: string[]     — specific set IDs to import (e.g., ["sv9", "base1"])
 *   recent?: number     — import sets from last N years
 *   newSets?: boolean   — auto-detect and import sets not yet in Shopify
 *   minPrice?: number   — skip cards below this market price (default: 0)
 *   maxPrice?: number   — skip cards above this market price (default: 500)
 *   dryRun?: boolean    — preview without creating products
 *
 * GET /api/pokemon/import
 *   List all available Pokemon TCG sets.
 */

export async function GET() {
  try {
    const result = await runPython(
      "pokemon-card-importer.py",
      ["--list-sets"],
      30000
    );

    if (result.exitCode !== 0) {
      return NextResponse.json(
        { error: "Failed to fetch sets", stderr: result.stderr },
        { status: 500 }
      );
    }

    // Parse the table output into structured data
    const lines = result.stdout.trim().split("\n");
    const sets: Array<{ id: string; name: string; cards: number; releaseDate: string }> = [];

    for (const line of lines) {
      // Match lines like: "  base1                Base                                          102  1999/01/09"
      const match = line.match(/^\s{2}(\S+)\s{2,}(.+?)\s{2,}(\d+)\s{2,}(\d{4}\/\d{2}\/\d{2})/);
      if (match) {
        sets.push({
          id: match[1],
          name: match[2].trim(),
          cards: parseInt(match[3]),
          releaseDate: match[4],
        });
      }
    }

    return NextResponse.json({ sets, total: sets.length });
  } catch (error) {
    console.error("Failed to list Pokemon sets:", error);
    return NextResponse.json({ error: "Failed to list sets" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { sets, recent, newSets, minPrice, maxPrice, dryRun } = body;

    const args: string[] = [];

    // Determine import mode
    if (sets && Array.isArray(sets) && sets.length > 0) {
      args.push("--set", ...sets);
    } else if (recent) {
      args.push("--recent", String(recent));
    } else if (newSets) {
      args.push("--new-sets");
    } else {
      return NextResponse.json(
        { error: "Must specify sets, recent, or newSets" },
        { status: 400 }
      );
    }

    if (minPrice !== undefined) args.push("--min-price", String(minPrice));
    if (maxPrice !== undefined) args.push("--max-price", String(maxPrice));
    if (dryRun) args.push("--dry-run");
    args.push("--save-csv");

    // Run with a generous timeout — large imports can take a while
    const timeoutMs = (sets?.length ?? 1) * 120000; // ~2 min per set
    const result = await runPython(
      "pokemon-card-importer.py",
      args,
      Math.min(timeoutMs, 600000) // cap at 10 min
    );

    // Parse results from output
    const output = result.stdout + result.stderr;
    const grandTotalMatch = output.match(
      /Cards processed:\s+(\d+)[\s\S]*?Created:\s+(\d+)[\s\S]*?No price data:\s+(\d+)[\s\S]*?Below min price:\s+(\d+)[\s\S]*?Above max price:\s+(\d+)[\s\S]*?Low profit:\s+(\d+)[\s\S]*?Failed:\s+(\d+)/
    );

    const summary = grandTotalMatch
      ? {
          cardsProcessed: parseInt(grandTotalMatch[1]),
          created: parseInt(grandTotalMatch[2]),
          noPrice: parseInt(grandTotalMatch[3]),
          belowMin: parseInt(grandTotalMatch[4]),
          aboveMax: parseInt(grandTotalMatch[5]),
          lowProfit: parseInt(grandTotalMatch[6]),
          failed: parseInt(grandTotalMatch[7]),
        }
      : null;

    return NextResponse.json({
      success: result.exitCode === 0,
      summary,
      output: result.stdout.slice(-2000), // Last 2000 chars of output
      dryRun: !!dryRun,
    });
  } catch (error) {
    console.error("Pokemon import failed:", error);
    return NextResponse.json({ error: "Import failed" }, { status: 500 });
  }
}
