import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export function useSocialPosts(params?: { status?: string; type?: string }) {
  return useQuery({
    queryKey: ["social-posts", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set("status", params.status);
      if (params?.type) searchParams.set("type", params.type);
      const res = await fetch(`/api/social/posts?${searchParams}`);
      if (!res.ok) throw new Error("Failed to fetch social posts");
      return res.json();
    },
  });
}

export function useScheduleSocialPosts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      postIds: number[];
      profileIds?: string[];
    }) => {
      const res = await fetch("/api/social/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!res.ok) throw new Error("Failed to schedule posts");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social-posts"] });
    },
  });
}

export function useSocialAnalytics() {
  return useQuery({
    queryKey: ["social-analytics"],
    queryFn: async () => {
      const res = await fetch("/api/social/analytics");
      if (!res.ok) throw new Error("Failed to fetch social analytics");
      return res.json();
    },
  });
}
