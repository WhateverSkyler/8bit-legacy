"use client";

import { useQuery } from "@tanstack/react-query";
import type { EbaySearchResult } from "@/types/ebay";

export function useEbaySearch(
  query: string,
  options?: { maxPrice?: number; condition?: string; enabled?: boolean }
) {
  return useQuery<EbaySearchResult>({
    queryKey: ["ebay-search", query, options?.maxPrice, options?.condition],
    queryFn: async () => {
      const params = new URLSearchParams({ q: query });
      if (options?.maxPrice)
        params.set("maxPrice", options.maxPrice.toString());
      if (options?.condition) params.set("condition", options.condition);

      const resp = await fetch(`/api/ebay/search?${params}`);
      if (!resp.ok) throw new Error("Failed to search eBay");
      return resp.json();
    },
    enabled: options?.enabled !== false && query.length > 0,
  });
}
