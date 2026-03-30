import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { FulfillmentTask, FulfillmentAlert } from "@/types/fulfillment";

export function useFulfillmentTasks(params?: { status?: string }) {
  return useQuery<{ tasks: FulfillmentTask[] }>({
    queryKey: ["fulfillment-tasks", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.status && params.status !== "all") {
        searchParams.set("status", params.status);
      }
      const res = await fetch(`/api/fulfillment/tasks?${searchParams}`);
      if (!res.ok) throw new Error("Failed to fetch fulfillment tasks");
      return res.json();
    },
  });
}

export function useCreateFulfillmentTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (task: {
      shopifyOrderId: string;
      shopifyOrderNumber: string;
      lineItemTitle: string;
      lineItemSku: string;
      lineItemPrice: number;
      lineItemQuantity: number;
      lineItemImageUrl?: string | null;
      customerName: string;
      customerCity: string;
    }) => {
      const res = await fetch("/api/fulfillment/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(task),
      });
      if (!res.ok) throw new Error("Failed to create fulfillment task");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fulfillment-tasks"] });
    },
  });
}

export function useUpdateFulfillmentTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...updates
    }: {
      id: number;
      status?: string;
      ebayOrderId?: string;
      ebayListingUrl?: string;
      ebayPurchasePrice?: number;
      ebaySellerName?: string;
      trackingNumber?: string;
      trackingCarrier?: string;
      notes?: string;
    }) => {
      const res = await fetch(`/api/fulfillment/tasks/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error("Failed to update fulfillment task");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fulfillment-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["fulfillment-alerts"] });
    },
  });
}

export function useCompleteFulfillment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (taskId: number) => {
      const res = await fetch(`/api/fulfillment/complete/${taskId}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to complete fulfillment");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fulfillment-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["fulfillment-alerts"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}

export function useFulfillmentAlerts() {
  return useQuery<{ alerts: FulfillmentAlert[] }>({
    queryKey: ["fulfillment-alerts"],
    queryFn: async () => {
      const res = await fetch("/api/fulfillment/alerts");
      if (!res.ok) throw new Error("Failed to fetch fulfillment alerts");
      return res.json();
    },
    refetchInterval: 60000, // refetch every minute
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (alertId: number) => {
      const res = await fetch("/api/fulfillment/alerts", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: alertId }),
      });
      if (!res.ok) throw new Error("Failed to acknowledge alert");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fulfillment-alerts"] });
    },
  });
}
