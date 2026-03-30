import "server-only";
import { db } from "@db/index";
import { settings } from "@db/schema";
import { eq } from "drizzle-orm";

// ── Hard Limits (cannot be overridden without code change) ─────────

export const HARD_LIMITS = {
  /** Maximum single price change as a fraction (0.30 = 30%) */
  MAX_PRICE_CHANGE_PERCENT: 0.30,
  /** Maximum daily ad spend in dollars */
  MAX_DAILY_AD_SPEND: 25,
  /** Maximum bid multiplier change per optimization run */
  MAX_BID_CHANGE_PERCENT: 0.20,
  /** Maximum products paused per optimization run */
  MAX_PRODUCTS_PAUSED_PER_RUN: 10,
  /** Maximum negative keywords added per week */
  MAX_NEGATIVE_KEYWORDS_PER_WEEK: 50,
  /** Never auto-price an item below its cost */
  NEVER_PRICE_BELOW_COST: true,
} as const;

// ── Soft Limits (configurable via Settings page) ───────────────────

export interface SoftLimits {
  /** Changes above this % require manual approval (default 15%) */
  priceAutoApplyThreshold: number;
  /** Minimum ROAS before allowing bid increase (default 500%) */
  minRoasForBidIncrease: number;
  /** Days of data required before auto-optimizing a product (default 7) */
  minDaysBeforeOptimize: number;
  /** Budget overspend alert threshold as multiplier (default 1.1 = 110%) */
  budgetOverspendAlert: number;
  /** Whether automated pricing is enabled */
  pricingAutoApplyEnabled: boolean;
  /** Whether to factor ad spend into profit calculation */
  factorAdSpend: boolean;
  /** Lookback window in days for ad cost calculation */
  adCostLookbackDays: number;
}

const DEFAULT_SOFT_LIMITS: SoftLimits = {
  priceAutoApplyThreshold: 0.15,
  minRoasForBidIncrease: 500,
  minDaysBeforeOptimize: 7,
  budgetOverspendAlert: 1.1,
  pricingAutoApplyEnabled: false,
  factorAdSpend: false,
  adCostLookbackDays: 30,
};

/**
 * Load soft limits from the settings table, with defaults.
 */
export function getSoftLimits(): SoftLimits {
  try {
    const row = db
      .select()
      .from(settings)
      .where(eq(settings.key, "automation_limits"))
      .get();

    if (row) {
      return { ...DEFAULT_SOFT_LIMITS, ...JSON.parse(row.value) };
    }
  } catch {
    // Fall through to defaults
  }
  return { ...DEFAULT_SOFT_LIMITS };
}

/**
 * Save soft limits to the settings table.
 */
export function saveSoftLimits(limits: Partial<SoftLimits>): void {
  const current = getSoftLimits();
  const merged = { ...current, ...limits };
  const now = new Date().toISOString();

  db.insert(settings)
    .values({ key: "automation_limits", value: JSON.stringify(merged), updatedAt: now })
    .onConflictDoUpdate({
      target: settings.key,
      set: { value: JSON.stringify(merged), updatedAt: now },
    })
    .run();
}

// ── Safety Check Functions ─────────────────────────────────────────

export interface SafetyResult {
  safe: boolean;
  action: "auto_apply" | "needs_review" | "rejected";
  reason?: string;
}

/**
 * Check if a price change is safe to auto-apply.
 */
export function checkPriceChangeSafety(
  oldPrice: number,
  newPrice: number,
  costPrice?: number
): SafetyResult {
  if (oldPrice <= 0) {
    return { safe: false, action: "rejected", reason: "Current price is zero or negative" };
  }

  const changePercent = Math.abs(newPrice - oldPrice) / oldPrice;
  const limits = getSoftLimits();

  // Hard limit: reject changes over 30%
  if (changePercent > HARD_LIMITS.MAX_PRICE_CHANGE_PERCENT) {
    return {
      safe: false,
      action: "rejected",
      reason: `Price change of ${(changePercent * 100).toFixed(1)}% exceeds hard limit of ${HARD_LIMITS.MAX_PRICE_CHANGE_PERCENT * 100}%`,
    };
  }

  // Never price below cost
  if (HARD_LIMITS.NEVER_PRICE_BELOW_COST && costPrice && newPrice < costPrice) {
    return {
      safe: false,
      action: "rejected",
      reason: `New price $${newPrice.toFixed(2)} is below cost $${costPrice.toFixed(2)}`,
    };
  }

  // Soft limit: changes between threshold and hard limit need review
  if (changePercent > limits.priceAutoApplyThreshold) {
    return {
      safe: false,
      action: "needs_review",
      reason: `Price change of ${(changePercent * 100).toFixed(1)}% exceeds auto-apply threshold of ${(limits.priceAutoApplyThreshold * 100).toFixed(1)}%`,
    };
  }

  return { safe: true, action: "auto_apply" };
}

/**
 * Check if an ad spend action is safe.
 */
export function checkAdSpendSafety(
  currentDailySpend: number,
  proposedAdditionalSpend: number
): SafetyResult {
  const totalSpend = currentDailySpend + proposedAdditionalSpend;

  if (totalSpend > HARD_LIMITS.MAX_DAILY_AD_SPEND) {
    return {
      safe: false,
      action: "rejected",
      reason: `Total daily spend $${totalSpend.toFixed(2)} would exceed limit of $${HARD_LIMITS.MAX_DAILY_AD_SPEND}`,
    };
  }

  const limits = getSoftLimits();
  if (totalSpend > HARD_LIMITS.MAX_DAILY_AD_SPEND * limits.budgetOverspendAlert) {
    return {
      safe: false,
      action: "needs_review",
      reason: `Daily spend approaching limit: $${totalSpend.toFixed(2)} / $${HARD_LIMITS.MAX_DAILY_AD_SPEND}`,
    };
  }

  return { safe: true, action: "auto_apply" };
}

/**
 * Check if a bid change is safe.
 */
export function checkBidChangeSafety(
  oldBid: number,
  newBid: number
): SafetyResult {
  if (oldBid <= 0) {
    return { safe: false, action: "rejected", reason: "Current bid is zero or negative" };
  }

  const changePercent = Math.abs(newBid - oldBid) / oldBid;

  if (changePercent > HARD_LIMITS.MAX_BID_CHANGE_PERCENT) {
    return {
      safe: false,
      action: "rejected",
      reason: `Bid change of ${(changePercent * 100).toFixed(1)}% exceeds limit of ${HARD_LIMITS.MAX_BID_CHANGE_PERCENT * 100}%`,
    };
  }

  return { safe: true, action: "auto_apply" };
}

// ── Circuit Breaker ────────────────────────────────────────────────

export type CircuitBreakerName = "pricing" | "google_ads";

interface CircuitBreakerState {
  tripped: boolean;
  reason: string;
  trippedAt: string;
}

/**
 * Trip a circuit breaker — blocks all automation for that system.
 */
export function tripCircuitBreaker(name: CircuitBreakerName, reason: string): void {
  const state: CircuitBreakerState = {
    tripped: true,
    reason,
    trippedAt: new Date().toISOString(),
  };
  const now = new Date().toISOString();

  db.insert(settings)
    .values({ key: `circuit_breaker_${name}`, value: JSON.stringify(state), updatedAt: now })
    .onConflictDoUpdate({
      target: settings.key,
      set: { value: JSON.stringify(state), updatedAt: now },
    })
    .run();

  console.error(`[Safety] Circuit breaker TRIPPED for ${name}: ${reason}`);
}

/**
 * Reset a circuit breaker — re-enables automation.
 */
export function resetCircuitBreaker(name: CircuitBreakerName): void {
  const state: CircuitBreakerState = {
    tripped: false,
    reason: "",
    trippedAt: "",
  };
  const now = new Date().toISOString();

  db.insert(settings)
    .values({ key: `circuit_breaker_${name}`, value: JSON.stringify(state), updatedAt: now })
    .onConflictDoUpdate({
      target: settings.key,
      set: { value: JSON.stringify(state), updatedAt: now },
    })
    .run();

  console.log(`[Safety] Circuit breaker RESET for ${name}`);
}

/**
 * Check if a circuit breaker is tripped.
 */
export function isCircuitBreakerTripped(name: CircuitBreakerName): { tripped: boolean; reason?: string; trippedAt?: string } {
  try {
    const row = db
      .select()
      .from(settings)
      .where(eq(settings.key, `circuit_breaker_${name}`))
      .get();

    if (row) {
      const state: CircuitBreakerState = JSON.parse(row.value);
      if (state.tripped) {
        return { tripped: true, reason: state.reason, trippedAt: state.trippedAt };
      }
    }
  } catch {
    // Fall through
  }
  return { tripped: false };
}

/**
 * Get status of all circuit breakers.
 */
export function getAllCircuitBreakerStatus(): Record<CircuitBreakerName, { tripped: boolean; reason?: string; trippedAt?: string }> {
  return {
    pricing: isCircuitBreakerTripped("pricing"),
    google_ads: isCircuitBreakerTripped("google_ads"),
  };
}
