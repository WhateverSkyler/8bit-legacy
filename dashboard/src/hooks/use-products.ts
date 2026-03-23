"use client";

import { useQuery } from "@tanstack/react-query";

export function useProducts(params?: {
  search?: string;
  console?: string;
  page?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.search) searchParams.set("search", params.search);
      if (params?.console) searchParams.set("console", params.console);
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.limit) searchParams.set("limit", params.limit.toString());

      const resp = await fetch(`/api/shopify/products?${searchParams}`);
      if (!resp.ok) throw new Error("Failed to fetch products");
      return resp.json();
    },
  });
}
