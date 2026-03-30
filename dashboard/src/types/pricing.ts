export interface PricingConfig {
  default_multiplier: number;
  minimum_profit_usd: number;
  shopify_fee_percent: number;
  shopify_fee_fixed: number;
  price_field: "loose" | "cib" | "new";
  round_to: number | null;
  category_multipliers: Record<string, number>;
  // Automation fields
  auto_apply_enabled?: boolean;
  auto_apply_threshold_percent?: number;
  max_price_change_percent?: number;
  factor_ad_spend?: boolean;
  ad_cost_lookback_days?: number;
}
