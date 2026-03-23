export interface Product {
  productId: string;
  title: string;
  handle: string;
  tags: string[];
  console: string;
  imageUrl: string | null;
  variants: ProductVariant[];
}

export interface ProductVariant {
  variantId: string;
  title: string;
  sku: string;
  price: number;
  barcode: string;
}

export interface ProductWithMetrics extends Product {
  marketPrice: number;
  sellPrice: number;
  profit: number;
  profitMargin: number;
  meetsMinProfit: boolean;
}

export interface PriceChartingItem {
  name: string;
  console: string;
  loosePrice: number;
  cibPrice: number;
  newPrice: number;
  upc: string;
  asin: string;
}

export interface PriceDiffRecord {
  productTitle: string;
  variantId: string;
  pcName: string;
  console: string;
  marketPrice: number;
  currentShopifyPrice: number;
  newPrice: number;
  priceDiff: number;
  estimatedProfit: number;
  meetsMinProfit: boolean;
  matchType: "upc" | "title_exact" | "title_console" | "fuzzy";
  selected?: boolean;
}

export interface PriceSyncRun {
  id: number;
  timestamp: string;
  totalItems: number;
  changesApplied: number;
  belowProfit: number;
  unmatched: number;
  netAdjustment: number;
}
