import "server-only";
import { db } from "@db/index";
import { settings, googleAdsPerformance } from "@db/schema";
import { eq, gte, sql } from "drizzle-orm";

// ── Hard Limits (cannot be overridden without code change) ─────────

export const HARD_LIMITS = {
  /** Maximum single price change as a fraction (0.30 = 30%) */
  MAX_PRICE_CHANGE_PERCENT: 0.30,
  /** Maximum daily ad spend in dollars.
   * Raised from $25 → $40 on 2026-04-20: new campaign base is $17/day and Google can
   * 2x a daily budget on any given day ($34). Old $25 would false-trip on normal
   * behavior. $40 keeps a ~2.3x guardrail above base while still catching runaways. */
  MAX_DAILY_AD_SPEND: 40,
  /** Maximum bid multiplier change per optimization run */
  MAX_BID_CHANGE_PERCENT: 0.20,
  /** Maximum products paused per optimization run */
  MAX_PRODUCTS_PAUSED_PER_RUN: 10,
  /** Maximum negative keywords added per week */
  MAX_NEGATIVE_KEYWORDS_PER_WEEK: 50,
  /** Never auto-price an item below its cost */
  NEVER_PRICE_BELOW_COST: true,
  /** Hard pause when cumulative spend hits this with 0 conversions.
   * Per user direction 2026-04-20: Shopping CPCs are cheap and intent-driven —
   * if $50 doesn't convert, the funnel is broken, not the ads. Don't buy more
   * runway past this point. */
  LIFETIME_NO_CONVERSION_CEILING: 50,
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

// ── Ads Safety Auto-Trip Conditions ───────────────────────────────

export interface AdsSafetyCheckResult {
  passed: boolean;
  checks: Array<{
    name: string;
    passed: boolean;
    detail: string;
  }>;
  tripped: boolean;
  tripReason?: string;
}

/**
 * Run all automatic safety checks for Google Ads.
 * Called by the ads-safety-check scheduled job every 6 hours.
 *
 * Uses the googleAdsPerformance table for spend/conversion data.
 * If any check fails, trips the google_ads circuit breaker.
 */
export function runAdsSafetyChecks(): AdsSafetyCheckResult {
  const checks: AdsSafetyCheckResult["checks"] = [];
  let shouldTrip = false;
  let tripReason = "";

  // Already tripped — skip checks
  const breaker = isCircuitBreakerTripped("google_ads");
  if (breaker.tripped) {
    return {
      passed: false,
      checks: [{ name: "circuit_breaker_status", passed: false, detail: `Already tripped: ${breaker.reason}` }],
      tripped: false,
    };
  }

  // ── Check 1: Daily spend > $25 hard limit ──
  const todayStr = new Date().toISOString().split("T")[0];
  const todaySpend = db
    .select({ total: sql<number>`coalesce(sum(cost), 0)` })
    .from(googleAdsPerformance)
    .where(eq(googleAdsPerformance.date, todayStr))
    .get();

  const dailySpend = todaySpend?.total ?? 0;
  const spendPassed = dailySpend <= HARD_LIMITS.MAX_DAILY_AD_SPEND;
  checks.push({
    name: "daily_spend_limit",
    passed: spendPassed,
    detail: `Today's spend: $${dailySpend.toFixed(2)} / $${HARD_LIMITS.MAX_DAILY_AD_SPEND} limit`,
  });
  if (!spendPassed) {
    shouldTrip = true;
    tripReason = `Daily spend $${dailySpend.toFixed(2)} exceeded $${HARD_LIMITS.MAX_DAILY_AD_SPEND} hard limit`;
  }

  // ── Check 2A: Lifetime cumulative trip (PRIMARY — user direction 2026-04-20) ──
  // Fires at $50 cumulative spent with 0 conversions — tighter and faster than the
  // 3-day check below, because Shopping CPCs are cheap/intent-driven and slow
  // accumulation shouldn't buy more runway past $50 with nothing to show.
  const lifetime = db
    .select({
      totalCost: sql<number>`coalesce(sum(cost), 0)`,
      totalConv: sql<number>`coalesce(sum(conversions), 0)`,
    })
    .from(googleAdsPerformance)
    .get();

  const lifetimeCost = lifetime?.totalCost ?? 0;
  const lifetimeConv = lifetime?.totalConv ?? 0;
  const lifetimeCeiling = HARD_LIMITS.LIFETIME_NO_CONVERSION_CEILING;
  const fiftyPassed = lifetimeCost < lifetimeCeiling || lifetimeConv > 0;
  checks.push({
    name: "lifetime_no_conversion_ceiling",
    passed: fiftyPassed,
    detail: `Lifetime: $${lifetimeCost.toFixed(2)} spent, ${lifetimeConv} conversions (hard pause at $${lifetimeCeiling} no-conv)`,
  });
  if (!fiftyPassed && !shouldTrip) {
    shouldTrip = true;
    tripReason = `Hard pause: $${lifetimeCost.toFixed(2)} cumulative spend with 0 conversions (floor $${lifetimeCeiling})`;
  }

  // ── Check 2B: 3 consecutive days with $10+ spend and 0 conversions (backup) ──
  // Kept as defense-in-depth. In practice 2A fires first, but this catches the
  // edge case where spend is paced so slowly that $50 hasn't accumulated yet but
  // three days in a row have still wasted $10+ each.
  const threeDaysAgo = new Date(Date.now() - 3 * 86400000).toISOString().split("T")[0];
  const recentDays = db
    .select({
      date: googleAdsPerformance.date,
      dayCost: sql<number>`sum(cost)`,
      dayConversions: sql<number>`sum(conversions)`,
    })
    .from(googleAdsPerformance)
    .where(gte(googleAdsPerformance.date, threeDaysAgo))
    .groupBy(googleAdsPerformance.date)
    .orderBy(googleAdsPerformance.date)
    .all();

  const qualifyingDays = recentDays.filter(d => d.dayCost >= 10 && d.dayConversions === 0);
  const noConvPassed = qualifyingDays.length < 3;
  checks.push({
    name: "consecutive_no_conversions",
    passed: noConvPassed,
    detail: `${qualifyingDays.length}/3 days with $10+ spend and 0 conversions`,
  });
  if (!noConvPassed && !shouldTrip) {
    shouldTrip = true;
    const totalWasted = qualifyingDays.reduce((sum, d) => sum + d.dayCost, 0);
    tripReason = `3 consecutive days with $10+ spend ($${totalWasted.toFixed(2)} total) and 0 conversions`;
  }

  // ── Check 3: Store downtime ──
  // This is an async check that should be called separately.
  // We record the last known state here. The job handler does the actual fetch.
  checks.push({
    name: "store_uptime",
    passed: true,
    detail: "Checked by job handler (async)",
  });

  // ── Check 4: Rolling 3-day ROAS < 200% after 7+ days of data ──
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString().split("T")[0];
  const hasEnoughData = db
    .select({ count: sql<number>`count(distinct date)` })
    .from(googleAdsPerformance)
    .where(gte(googleAdsPerformance.date, sevenDaysAgo))
    .get();

  if ((hasEnoughData?.count ?? 0) >= 7) {
    const rollingPerf = db
      .select({
        totalCost: sql<number>`coalesce(sum(cost), 0)`,
        totalValue: sql<number>`coalesce(sum(conversion_value), 0)`,
      })
      .from(googleAdsPerformance)
      .where(gte(googleAdsPerformance.date, threeDaysAgo))
      .get();

    const cost = rollingPerf?.totalCost ?? 0;
    const value = rollingPerf?.totalValue ?? 0;
    const rollingRoas = cost > 0 ? (value / cost) * 100 : 0;
    const roasPassed = rollingRoas >= 200 || cost === 0;

    checks.push({
      name: "rolling_roas_floor",
      passed: roasPassed,
      detail: `3-day ROAS: ${Math.round(rollingRoas)}% (floor: 200%, requires 7+ days data)`,
    });
    if (!roasPassed && !shouldTrip) {
      shouldTrip = true;
      tripReason = `Rolling 3-day ROAS dropped to ${Math.round(rollingRoas)}% (below 200% floor after 7+ days of data)`;
    }
  } else {
    checks.push({
      name: "rolling_roas_floor",
      passed: true,
      detail: `Only ${hasEnoughData?.count ?? 0}/7 days of data — ROAS check deferred`,
    });
  }

  // Trip the breaker if any check failed
  if (shouldTrip) {
    tripCircuitBreaker("google_ads", tripReason);
  }

  return {
    passed: !shouldTrip,
    checks,
    tripped: shouldTrip,
    tripReason: shouldTrip ? tripReason : undefined,
  };
}
