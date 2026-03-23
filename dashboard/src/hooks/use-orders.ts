"use client";

import { useQuery } from "@tanstack/react-query";

export function useOrders(params?: {
  status?: "all" | "unfulfilled" | "fulfilled";
  search?: string;
  page?: number;
}) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.status && params.status !== "all")
        searchParams.set("status", params.status);
      if (params?.search) searchParams.set("search", params.search);
      if (params?.page) searchParams.set("page", params.page.toString());

      const resp = await fetch(`/api/shopify/orders?${searchParams}`);
      if (!resp.ok) throw new Error("Failed to fetch orders");
      return resp.json();
    },
  });
}
