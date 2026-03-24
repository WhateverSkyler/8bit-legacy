"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

export function usePriceSyncUpload() {
  return useMutation({
    mutationFn: async (csvText: string) => {
      const resp = await fetch("/api/price-sync/upload", {
        method: "POST",
        headers: { "Content-Type": "text/csv" },
        body: csvText,
      });
      if (!resp.ok) throw new Error("Failed to upload CSV");
      return resp.json();
    },
  });
}

export function usePriceSyncDiff() {
  return useMutation({
    mutationFn: async (payload: {
      pcItems: unknown[];
      minChange?: number;
    }) => {
      const resp = await fetch("/api/price-sync/diff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Failed to generate diff");
      return resp.json();
    },
  });
}

export function usePriceSyncApply() {
  return useMutation({
    mutationFn: async (changes: { variantId: string; newPrice: number; productTitle?: string; marketPrice?: number; oldPrice?: number; priceDiff?: number; estimatedProfit?: number }[]) => {
      const resp = await fetch("/api/price-sync/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ changes }),
      });
      if (!resp.ok) throw new Error("Failed to apply price changes");
      return resp.json();
    },
  });
}

export function usePriceSyncHistory() {
  return useQuery({
    queryKey: ["price-sync-history"],
    queryFn: async () => {
      const resp = await fetch("/api/price-sync/history");
      if (!resp.ok) throw new Error("Failed to fetch sync history");
      return resp.json();
    },
  });
}
