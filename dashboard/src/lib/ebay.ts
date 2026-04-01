import "server-only";
import type { EbayListing, EbaySearchResult } from "@/types/ebay";

const EBAY_SEARCH_URL =
  "https://api.ebay.com/buy/browse/v1/item_summary/search";
const EBAY_TOKEN_URL =
  "https://api.ebay.com/identity/v1/oauth2/token";

// Cached OAuth token with expiry
let _cachedToken: { token: string; expiresAt: number } | null = null;

/**
 * Exchange App ID + Cert ID for an OAuth access token.
 * Tokens are cached until they expire (typically 2 hours).
 */
async function getEbayAccessToken(appId: string, certId: string): Promise<string | null> {
  if (_cachedToken && Date.now() < _cachedToken.expiresAt) {
    return _cachedToken.token;
  }

  const credentials = Buffer.from(`${appId}:${certId}`).toString("base64");
  try {
    const resp = await fetch(EBAY_TOKEN_URL, {
      method: "POST",
      headers: {
        Authorization: `Basic ${credentials}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: "grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope",
    });

    if (!resp.ok) {
      console.error(`eBay token error: ${resp.status}`);
      return null;
    }

    const data = await resp.json();
    _cachedToken = {
      token: data.access_token,
      expiresAt: Date.now() + (data.expires_in - 60) * 1000, // refresh 60s early
    };
    return _cachedToken.token;
  } catch (error) {
    console.error("eBay token error:", error);
    return null;
  }
}

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
    certId?: string;
  } = {}
): Promise<EbaySearchResult> {
  const { maxPrice, condition = "USED", limit = 20, certId } = options;

  if (!appId || !certId) {
    return {
      query,
      results: [],
      isFallback: true,
    };
  }

  const accessToken = await getEbayAccessToken(appId, certId);
  if (!accessToken) {
    return { query, results: [], isFallback: true };
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
        Authorization: `Bearer ${accessToken}`,
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
