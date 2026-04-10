"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export interface SchedulerJob {
  name: string;
  cron: string;
  enabled: boolean;
  running: boolean;
  description: string;
  lastRun?: {
    id: number;
    status: string;
    finishedAt: string | null;
    itemsProcessed: number | null;
    itemsChanged: number | null;
  };
}

export interface CircuitBreaker {
  name: string;
  tripped: boolean;
  tripCount: number;
  lastTripped: string | null;
}

interface SchedulerStatus {
  jobs: SchedulerJob[];
  circuitBreakers: CircuitBreaker[];
  timestamp: string;
}

export function useSchedulerStatus() {
  return useQuery<SchedulerStatus>({
    queryKey: ["scheduler-status"],
    queryFn: async () => {
      const res = await fetch("/api/scheduler/status");
      if (!res.ok) throw new Error("Failed to fetch scheduler status");
      return res.json();
    },
    refetchInterval: 15_000, // Refresh every 15s
  });
}

export function useRunJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobName: string) => {
      const res = await fetch(`/api/scheduler/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobName }),
      });
      if (!res.ok) throw new Error("Failed to trigger job");
      return res.json();
    },
    onSuccess: () => {
      // Refetch status after triggering
      queryClient.invalidateQueries({ queryKey: ["scheduler-status"] });
    },
  });
}
