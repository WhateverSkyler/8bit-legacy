import "server-only";
import type { EbayListing, EbaySearchResult } from "@/types/ebay";

const EBAY_SEARCH_URL =
  "https://api.ebay.com/buy/browse/v1/item_summary/search";

/**
 * Search eBay via Browse API for matching listings.
 * Ported from Python's search_ebay_api()
 */
export async function searchEbay(
  query: string,
  appId: string,
  options: {
    maxPrice?: number;
    condition?: "USED" | "NEW" | "ANY";
    limit?: number;
  } = {}
): Promise<EbaySearchResult> {
  const { maxPrice, condition = "USED", limit = 20 } = options;

  if (!appId) {
    return {
      query,
      results: [],
      isFallback: true,
    };
  }

  let filter = "buyingOptions:{FIXED_PRICE},deliveryCountry:US";
  if (maxPrice) {
    filter += `,price:[..${maxPrice}],priceCurrency:USD`;
  }
  if (condition !== "ANY") {
    filter += `,conditions:{${condition}}`;
  }

  const params = new URLSearchParams({
    q: query,
    sort: "price",
    limit: limit.toString(),
    filter,
  });

  try {
    const resp = await fetch(`${EBAY_SEARCH_URL}?${params}`, {
      headers: {
        Authorization: `Bearer ${appId}`,
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Content-Type": "application/json",
      },
    });

    if (!resp.ok) {
      console.error(`eBay API error: ${resp.status}`);
      return { query, results: [], isFallback: true };
    }

    const data = await resp.json();
    const items: EbayListing[] = (data.itemSummaries ?? []).map(
      (item: any) => {
        const price = parseFloat(item.price?.value ?? "0");
        const shippingOptions = item.shippingOptions ?? [];
        const shippingCost = shippingOptions.length > 0
          ? parseFloat(shippingOptions[0]?.shippingCost?.value ?? "0")
          : 0;

        return {
          title: item.title ?? "",
          price,
          shipping: shippingCost,
          total: Math.round((price + shippingCost) * 100) / 100,
          condition: item.condition ?? "",
          url: item.itemWebUrl ?? "",
          seller: item.seller?.username ?? "",
          sellerFeedback: item.seller?.feedbackPercentage ?? "",
          imageUrl: item.image?.imageUrl ?? "",
        };
      }
    );

    // Sort by total cost
    items.sort((a, b) => a.total - b.total);

    return { query, results: items, isFallback: false };
  } catch (error) {
    console.error("eBay search error:", error);
    return { query, results: [], isFallback: true };
  }
}

/**
 * Generate eBay search URL as fallback when API isn't configured.
 * Ported from Python's search_ebay_web_fallback()
 */
export function getEbaySearchUrl(
  query: string,
  maxPrice?: number
): string {
  const params = new URLSearchParams({
    _nkw: query,
    _sop: "15", // Sort by price + shipping lowest first
    LH_BIN: "1", // Buy It Now only
    LH_PrefLoc: "1", // US only
  });

  if (maxPrice) {
    params.set("_udhi", maxPrice.toString());
  }

  return `https://www.ebay.com/sch/i.html?${params}`;
}
