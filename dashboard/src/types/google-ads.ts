export interface CampaignMetrics {
  date: string;
  campaignId: string;
  campaignName: string;
  impressions: number;
  clicks: number;
  cost: number;
  conversions: number;
  conversionValue: number;
  roas: number;
  cpc: number;
}

export interface ProductMetrics {
  date: string;
  productId: string;
  productTitle: string;
  impressions: number;
  clicks: number;
  cost: number;
  conversions: number;
  conversionValue: number;
  roas: number;
  cpc: number;
}

export interface SearchTermEntry {
  searchTerm: string;
  campaignId: string;
  impressions: number;
  clicks: number;
  cost: number;
  conversions: number;
  suggestedAction: "keep" | "add_negative" | "review";
}

export interface AdAction {
  id: number;
  runId: number | null;
  actionType: string;
  targetEntityType: string;
  targetEntityId: string;
  targetEntityName: string;
  oldValue: string | null;
  newValue: string | null;
  reason: string;
  executedAt: string;
  success: boolean;
  errorMessage: string | null;
}

export type AdActionType =
  | "bid_increase"
  | "bid_decrease"
  | "pause_product"
  | "unpause_product"
  | "add_negative_keyword"
  | "budget_adjust";
