import "server-only";
import { db } from "@db/index";
import { priceSnapshots, fulfillmentAlerts, fulfillmentTasks } from "@db/schema";
import { desc, eq } from "drizzle-orm";
import { getPricingConfig } from "./config";
import { calculateProfit } from "./pricing";
import type { Order, OrderLineItem } from "@/types/order";

export interface PriceValidationResult {
  orderId: string;
  orderNumber: string;
  lineItem: OrderLineItem;
  sellingPrice: number;
  marketPrice: number;
  estimatedProfit: number;
  status: "profitable" | "thin_margin" | "loss";
  message: string;
}

/**
 * Validate all line items in unfulfilled orders against current market prices.
 * Creates fulfillment alerts for items that would be sold at a loss or thin margin.
 * Returns counts of issues found.
 */
export function validateOrderPrices(orders: Order[]): {
  validated: number;
  losses: number;
  thinMargins: number;
  alertsCreated: number;
  results: PriceValidationResult[];
} {
  const config = getPricingConfig();
  const results: PriceValidationResult[] = [];
  let alertsCreated = 0;

  // Load all recent price snapshots (most recent per product title)
  const snapshots = db
    .select()
    .from(priceSnapshots)
    .orderBy(desc(priceSnapshots.scrapedAt))
    .all();

  // Build a lookup map: normalized title → most recent snapshot
  const snapshotByTitle = new Map<string, typeof snapshots[0]>();
  for (const snap of snapshots) {
    const key = snap.productTitle.toLowerCase().trim();
    if (!snapshotByTitle.has(key)) {
      snapshotByTitle.set(key, snap);
    }
  }

  for (const order of orders) {
    // Check if this order already has fulfillment tasks created
    const existingTasks = db
      .select()
      .from(fulfillmentTasks)
      .where(eq(fulfillmentTasks.shopifyOrderId, order.id))
      .all();

    for (const lineItem of order.lineItems) {
      // Skip if a fulfillment task already exists for this line item
      const hasTask = existingTasks.some(
        (t) => t.lineItemTitle === lineItem.title
      );

      // Find matching price snapshot
      const snapshot = findMatchingSnapshot(lineItem.title, snapshotByTitle);

      if (!snapshot) {
        // No price data — we can't validate, but create the task if needed
        if (!hasTask) {
          createFulfillmentTask(order, lineItem);
        }
        continue;
      }

      const marketPrice = snapshot.loosePrice;
      const sellingPrice = lineItem.price;
      const profit = calculateProfit(sellingPrice, marketPrice, config);

      let status: PriceValidationResult["status"];
      let message: string;

      if (profit < 0) {
        status = "loss";
        message = `LOSS: "${lineItem.title}" sells for $${sellingPrice.toFixed(2)} but market price is $${marketPrice.toFixed(2)} (loss of $${Math.abs(profit).toFixed(2)} after fees)`;
      } else if (profit < config.minimum_profit_usd) {
        status = "thin_margin";
        message = `LOW MARGIN: "${lineItem.title}" profit is only $${profit.toFixed(2)} (below $${config.minimum_profit_usd.toFixed(2)} threshold)`;
      } else {
        status = "profitable";
        message = `OK: "${lineItem.title}" profit $${profit.toFixed(2)}`;
      }

      results.push({
        orderId: order.id,
        orderNumber: order.orderNumber,
        lineItem,
        sellingPrice,
        marketPrice,
        estimatedProfit: profit,
        status,
        message,
      });

      // Create alerts for problematic items
      if (status === "loss" || status === "thin_margin") {
        // Check if we already alerted for this exact order+item
        const existingAlert = db
          .select()
          .from(fulfillmentAlerts)
          .where(eq(fulfillmentAlerts.message, message))
          .all();

        if (existingAlert.length === 0) {
          const taskForItem = existingTasks.find(
            (t) => t.lineItemTitle === lineItem.title
          );

          db.insert(fulfillmentAlerts)
            .values({
              taskId: taskForItem?.id ?? null,
              type: status === "loss" ? "cost_overrun" : "thin_margin",
              message,
              severity: status === "loss" ? "critical" : "warning",
              acknowledged: 0,
              createdAt: new Date().toISOString(),
            })
            .run();

          alertsCreated++;
        }
      }

      // Create fulfillment task if doesn't exist
      if (!hasTask) {
        createFulfillmentTask(order, lineItem);
      }
    }
  }

  const losses = results.filter((r) => r.status === "loss").length;
  const thinMargins = results.filter((r) => r.status === "thin_margin").length;

  return {
    validated: results.length,
    losses,
    thinMargins,
    alertsCreated,
    results,
  };
}

/**
 * Find a matching price snapshot for an order line item title.
 * Uses progressive matching: exact → contains → fuzzy.
 */
function findMatchingSnapshot(
  title: string,
  snapshotByTitle: Map<string, { productTitle: string; loosePrice: number; cibPrice: number | null; newPrice: number | null }>
): { productTitle: string; loosePrice: number } | null {
  const normalized = title.toLowerCase().trim();

  // Exact match
  if (snapshotByTitle.has(normalized)) {
    return snapshotByTitle.get(normalized)!;
  }

  // Substring match — snapshot title in order title or vice versa
  for (const [key, snap] of snapshotByTitle) {
    if (normalized.includes(key) || key.includes(normalized)) {
      return snap;
    }
  }

  // Strip common suffixes like " - NES", " - Nintendo 64", etc. and try again
  const stripped = normalized
    .replace(/\s*[-–—]\s*(nes|snes|n64|nintendo 64|gameboy|game boy|genesis|ps1|ps2|gamecube|dreamcast|saturn|gba|playstation|xbox|wii|switch|pokemon|pokémon).*$/i, "")
    .trim();

  if (stripped !== normalized) {
    for (const [key, snap] of snapshotByTitle) {
      if (stripped.includes(key) || key.includes(stripped)) {
        return snap;
      }
    }
  }

  return null;
}

/**
 * Create a fulfillment task for an order line item.
 */
function createFulfillmentTask(order: Order, lineItem: OrderLineItem): void {
  db.insert(fulfillmentTasks)
    .values({
      shopifyOrderId: order.id,
      shopifyOrderNumber: order.orderNumber,
      lineItemTitle: lineItem.title,
      lineItemSku: lineItem.sku,
      lineItemPrice: lineItem.price,
      lineItemQuantity: lineItem.quantity,
      lineItemImageUrl: lineItem.imageUrl,
      status: "pending",
      customerName: order.customerName,
      customerCity: order.customerCity,
      createdAt: new Date().toISOString(),
    })
    .run();
}
