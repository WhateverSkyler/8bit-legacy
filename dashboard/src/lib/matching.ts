import type { PriceChartingItem, PriceDiffRecord } from "@/types/product";
import type { PricingConfig } from "@/types/pricing";
import { calculateSellPrice, calculateProfit, checkMinimumProfit } from "./pricing";

export type MatchType = "upc" | "title_exact" | "title_console" | "fuzzy";

export interface ShopifyProduct {
  productId: string;
  productTitle: string;
  productHandle: string;
  productTags: string[];
  variantId: string;
  variantTitle: string;
  sku: string;
  currentPrice: number;
  barcode: string;
}

export interface ProductMatch {
  pc: PriceChartingItem;
  shopify: ShopifyProduct;
  matchType: MatchType;
}

/**
 * Match PriceCharting items to Shopify products by title similarity.
 * Ported from Python's match_products()
 *
 * Match priority: UPC/barcode → exact title → title+console → fuzzy substring
 */
export function matchProducts(
  pcItems: PriceChartingItem[],
  shopifyProducts: ShopifyProduct[]
): { matches: ProductMatch[]; unmatched: PriceChartingItem[] } {
  const matches: ProductMatch[] = [];
  const unmatched: PriceChartingItem[] = [];

  // Build lookup maps
  const shopifyByTitle = new Map<string, ShopifyProduct>();
  const shopifyByBarcode = new Map<string, ShopifyProduct>();

  for (const sp of shopifyProducts) {
    const normalized = sp.productTitle.toLowerCase().trim();
    shopifyByTitle.set(normalized, sp);
    if (sp.barcode) {
      shopifyByBarcode.set(sp.barcode, sp);
    }
  }

  for (const pcItem of pcItems) {
    // Try UPC/barcode match first (most reliable)
    if (pcItem.upc && shopifyByBarcode.has(pcItem.upc)) {
      matches.push({
        pc: pcItem,
        shopify: shopifyByBarcode.get(pcItem.upc)!,
        matchType: "upc",
      });
      continue;
    }

    // Try exact title match
    const pcTitle = pcItem.name.toLowerCase().trim();
    if (shopifyByTitle.has(pcTitle)) {
      matches.push({
        pc: pcItem,
        shopify: shopifyByTitle.get(pcTitle)!,
        matchType: "title_exact",
      });
      continue;
    }

    // Try title with console
    const pcTitleConsole =
      `${pcItem.name} - ${pcItem.console}`.toLowerCase().trim();
    if (shopifyByTitle.has(pcTitleConsole)) {
      matches.push({
        pc: pcItem,
        shopify: shopifyByTitle.get(pcTitleConsole)!,
        matchType: "title_console",
      });
      continue;
    }

    // Try fuzzy: PC title contained in Shopify title or vice versa
    let matched = false;
    for (const [normalized, sp] of shopifyByTitle.entries()) {
      if (pcTitle.includes(normalized) || normalized.includes(pcTitle)) {
        matches.push({ pc: pcItem, shopify: sp, matchType: "fuzzy" });
        matched = true;
        break;
      }
    }

    if (!matched) {
      unmatched.push(pcItem);
    }
  }

  return { matches, unmatched };
}

/**
 * Generate a diff of price changes needed.
 * Ported from Python's generate_diff()
 */
export function generateDiff(
  matches: ProductMatch[],
  config: PricingConfig,
  minChange: number = 0.5
): {
  changes: PriceDiffRecord[];
  skippedProfit: PriceDiffRecord[];
  noChange: PriceDiffRecord[];
} {
  const changes: PriceDiffRecord[] = [];
  const skippedProfit: PriceDiffRecord[] = [];
  const noChange: PriceDiffRecord[] = [];

  for (const match of matches) {
    const { pc, shopify } = match;

    // Get market price based on config field
    const priceField = config.price_field || "loose";
    let marketPrice: number;
    switch (priceField) {
      case "cib":
        marketPrice = pc.cibPrice || pc.loosePrice;
        break;
      case "new":
        marketPrice = pc.newPrice || pc.loosePrice;
        break;
      default:
        marketPrice = pc.loosePrice;
    }

    const newPrice = calculateSellPrice(marketPrice, config);
    const currentPrice = shopify.currentPrice;
    const priceDiff = Math.round((newPrice - currentPrice) * 100) / 100;
    const meetsProfit = checkMinimumProfit(newPrice, marketPrice, config);
    const profit = calculateProfit(newPrice, marketPrice, config);

    const record: PriceDiffRecord = {
      productTitle: shopify.productTitle,
      variantId: shopify.variantId,
      pcName: pc.name,
      console: pc.console,
      marketPrice,
      currentShopifyPrice: currentPrice,
      newPrice,
      priceDiff,
      estimatedProfit: profit,
      meetsMinProfit: meetsProfit,
      matchType: match.matchType,
    };

    if (!meetsProfit) {
      skippedProfit.push(record);
    } else if (Math.abs(priceDiff) < minChange) {
      noChange.push(record);
    } else if (priceDiff !== 0) {
      changes.push(record);
    } else {
      noChange.push(record);
    }
  }

  return { changes, skippedProfit, noChange };
}
