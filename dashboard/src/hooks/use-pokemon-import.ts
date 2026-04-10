"use client";

import { useQuery, useMutation } from "@tanstack/react-query";

export interface PokemonSet {
  id: string;
  name: string;
  cards: number;
  releaseDate: string;
  imported: boolean;
}

interface ImportResult {
  success: boolean;
  summary: {
    total: number;
    created: number;
    noPrice: number;
    belowMin: number;
    aboveMax: number;
    lowProfit: number;
    failed: number;
  };
  output: string;
}

export function usePokemonSets() {
  return useQuery<{ sets: PokemonSet[] }>({
    queryKey: ["pokemon-sets"],
    queryFn: async () => {
      const res = await fetch("/api/pokemon/import");
      if (!res.ok) throw new Error("Failed to fetch sets");
      return res.json();
    },
  });
}

export function usePokemonImport() {
  return useMutation<ImportResult, Error, { sets: string[]; dryRun: boolean; minPrice: number; maxPrice: number }>({
    mutationFn: async ({ sets, dryRun, minPrice, maxPrice }) => {
      const res = await fetch("/api/pokemon/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "specific",
          sets,
          dryRun,
          minPrice,
          maxPrice,
        }),
      });
      if (!res.ok) throw new Error("Import failed");
      return res.json();
    },
  });
}
