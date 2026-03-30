import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export function useAdsPerformance(params?: { dateRange?: string; entityType?: string }) {
  return useQuery({
    queryKey: ["ads-performance", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.dateRange) searchParams.set("dateRange", params.dateRange);
      if (params?.entityType) searchParams.set("entityType", params.entityType);
      const res = await fetch(`/api/google-ads/performance?${searchParams}`);
      if (!res.ok) throw new Error("Failed to fetch ads performance");
      return res.json();
    },
  });
}

export function useAdsSearchTerms() {
  return useQuery({
    queryKey: ["ads-search-terms"],
    queryFn: async () => {
      const res = await fetch("/api/google-ads/search-terms");
      if (!res.ok) throw new Error("Failed to fetch search terms");
      return res.json();
    },
  });
}

export function useAdsSyncData() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/google-ads/sync", { method: "POST" });
      if (!res.ok) throw new Error("Failed to sync ads data");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ads-performance"] });
      queryClient.invalidateQueries({ queryKey: ["ads-search-terms"] });
      queryClient.invalidateQueries({ queryKey: ["ads-actions"] });
    },
  });
}

export function useAdsOptimize() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/google-ads/optimize", { method: "POST" });
      if (!res.ok) throw new Error("Failed to run optimization");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ads-performance"] });
      queryClient.invalidateQueries({ queryKey: ["ads-actions"] });
    },
  });
}

export function useAdsActions() {
  return useQuery({
    queryKey: ["ads-actions"],
    queryFn: async () => {
      const res = await fetch("/api/google-ads/actions");
      if (!res.ok) throw new Error("Failed to fetch ads actions");
      return res.json();
    },
  });
}

export function useExecuteAdAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (action: {
      actionType: string;
      targetEntityType: string;
      targetEntityId: string;
      targetEntityName: string;
      reason: string;
    }) => {
      const res = await fetch("/api/google-ads/actions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action),
      });
      if (!res.ok) throw new Error("Failed to execute ad action");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ads-actions"] });
      queryClient.invalidateQueries({ queryKey: ["ads-performance"] });
    },
  });
}
