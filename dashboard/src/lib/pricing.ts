import type { PricingConfig } from "@/types/pricing";

/**
 * Pricing engine — ported from scripts/price-sync.py
 * These functions are pure (no side effects) and can run on both server and client.
 */

/**
 * Calculate the selling price based on market price and multiplier.
 * Ported from Python's calculate_sell_price()
 */
export function calculateSellPrice(
  marketPrice: number,
  config: PricingConfig,
  category: string = "retro_games"
): number {
  const multiplier =
    config.category_multipliers[category] ?? config.default_multiplier;
  const rawPrice = marketPrice * multiplier;

  // Round to .99 if configured
  if (config.round_to !== null && config.round_to !== undefined) {
    let rounded = Math.ceil(rawPrice) - (1 - config.round_to);
    // Don't go below the raw price
    if (rounded < rawPrice) {
      rounded += 1.0;
    }
    return Math.round(rounded * 100) / 100;
  }

  return Math.round(rawPrice * 100) / 100;
}

/**
 * Calculate estimated profit after Shopify fees.
 * Ported from Python's calculate_profit()
 */
export function calculateProfit(
  sellPrice: number,
  marketPrice: number,
  config: PricingConfig
): number {
  const shopifyFee =
    sellPrice * config.shopify_fee_percent + config.shopify_fee_fixed;
  return Math.round((sellPrice - marketPrice - shopifyFee) * 100) / 100;
}

/**
 * Check if the item meets minimum profit threshold.
 * Ported from Python's check_minimum_profit()
 */
export function checkMinimumProfit(
  sellPrice: number,
  marketPrice: number,
  config: PricingConfig
): boolean {
  const profit = calculateProfit(sellPrice, marketPrice, config);
  return profit >= config.minimum_profit_usd;
}

/**
 * Calculate profit margin as a percentage.
 */
export function calculateProfitMargin(
  sellPrice: number,
  marketPrice: number,
  config: PricingConfig
): number {
  if (sellPrice === 0) return 0;
  const profit = calculateProfit(sellPrice, marketPrice, config);
  return Math.round((profit / sellPrice) * 1000) / 10;
}

/**
 * Parse a price string like '$12.99' or '12.99' to number.
 * Ported from Python's parse_price()
 */
export function parsePrice(priceStr: string): number {
  if (!priceStr) return 0;
  const cleaned = priceStr.replace(/[$,]/g, "").trim();
  const value = parseFloat(cleaned);
  return isNaN(value) ? 0 : value;
}

/**
 * Calculate profit factoring in ad spend per order.
 * Used by the smart margin engine.
 */
export function calculateProfitWithAdCost(
  sellPrice: number,
  marketPrice: number,
  config: PricingConfig,
  adCostPerUnit: number = 0
): number {
  const shopifyFee =
    sellPrice * config.shopify_fee_percent + config.shopify_fee_fixed;
  return Math.round((sellPrice - marketPrice - shopifyFee - adCostPerUnit) * 100) / 100;
}

/**
 * Calculate the minimum multiplier needed to hit the profit threshold,
 * accounting for fees and optional ad cost.
 */
export function getRequiredMultiplier(
  marketPrice: number,
  config: PricingConfig,
  adCostPerUnit: number = 0,
  targetProfit?: number
): number {
  if (marketPrice <= 0) return config.default_multiplier;
  const minProfit = targetProfit ?? config.minimum_profit_usd;
  // sellPrice = marketPrice * multiplier
  // profit = sellPrice - marketPrice - (sellPrice * feePercent + feeFixed) - adCost >= minProfit
  // sellPrice * (1 - feePercent) = marketPrice + feeFixed + adCost + minProfit
  // sellPrice = (marketPrice + feeFixed + adCost + minProfit) / (1 - feePercent)
  const requiredSellPrice =
    (marketPrice + config.shopify_fee_fixed + adCostPerUnit + minProfit) /
    (1 - config.shopify_fee_percent);
  return Math.round((requiredSellPrice / marketPrice) * 100) / 100;
}
