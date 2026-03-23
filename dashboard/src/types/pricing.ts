export interface PricingConfig {
  default_multiplier: number;
  minimum_profit_usd: number;
  shopify_fee_percent: number;
  shopify_fee_fixed: number;
  price_field: "loose" | "cib" | "new";
  round_to: number | null;
  category_multipliers: Record<string, number>;
}
