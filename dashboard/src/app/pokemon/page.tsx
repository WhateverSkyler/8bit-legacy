"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import {
  Download,
  Eye,
  Loader2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Search,
} from "lucide-react";
import { usePokemonSets, usePokemonImport } from "@/hooks/use-pokemon-import";

export default function PokemonImportPage() {
  const { data: setsData, isLoading, refetch } = usePokemonSets();
  const importMutation = usePokemonImport();

  const [selectedSets, setSelectedSets] = useState<Set<string>>(new Set());
  const [minPrice, setMinPrice] = useState(5);
  const [maxPrice, setMaxPrice] = useState(500);
  const [searchQuery, setSearchQuery] = useState("");
  const [lastResult, setLastResult] = useState<{
    success: boolean;
    summary: Record<string, number>;
  } | null>(null);

  const sets = setsData?.sets ?? [];
  const filteredSets = sets.filter(
    (s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleSet = (id: string) => {
    setSelectedSets((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllUnimported = () => {
    const unimported = sets.filter((s) => !s.imported).map((s) => s.id);
    setSelectedSets(new Set(unimported));
  };

  const runImport = (dryRun: boolean) => {
    if (selectedSets.size === 0) return;
    importMutation.mutate(
      { sets: Array.from(selectedSets), dryRun, minPrice, maxPrice },
      {
        onSuccess: (data) => {
          setLastResult(data);
          if (!dryRun) refetch();
        },
      }
    );
  };

  const importedCount = sets.filter((s) => s.imported).length;
  const totalSets = sets.length;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Pokemon Card Import"
        description="Import Pokemon TCG cards from the Pokemon TCG API into Shopify."
      >
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={14} />
          Refresh Sets
        </Button>
      </PageHeader>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Total Sets</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-text-primary">{totalSets}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Imported</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-green-600">{importedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Available</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-accent-cyan">{totalSets - importedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Selected</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-orange-500">{selectedSets.size}</p>
          </CardContent>
        </Card>
      </div>

      {/* Import Controls */}
      <Card>
        <CardContent>
          <h2 className="text-sm font-semibold text-text-primary">Import Settings</h2>
          <div className="mt-4 flex flex-wrap items-end gap-4">
            <div>
              <label className="text-xs font-medium text-text-muted">Min Market Price ($)</label>
              <input
                type="number"
                value={minPrice}
                onChange={(e) => setMinPrice(Number(e.target.value))}
                className="mt-1 block w-24 rounded-[var(--radius-md)] border border-border bg-bg-surface px-3 py-2 text-sm"
                step="1"
                min="0"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-text-muted">Max Market Price ($)</label>
              <input
                type="number"
                value={maxPrice}
                onChange={(e) => setMaxPrice(Number(e.target.value))}
                className="mt-1 block w-24 rounded-[var(--radius-md)] border border-border bg-bg-surface px-3 py-2 text-sm"
                step="1"
                min="0"
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={selectedSets.size === 0 || importMutation.isPending}
                onClick={() => runImport(true)}
              >
                <Eye size={14} />
                Dry Run ({selectedSets.size})
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={selectedSets.size === 0 || importMutation.isPending}
                onClick={() => runImport(false)}
              >
                {importMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Download size={14} />
                )}
                Import ({selectedSets.size})
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Import Result */}
      {lastResult && (
        <Card>
          <CardContent>
            <div className="flex items-center gap-2">
              {lastResult.success ? (
                <CheckCircle2 size={18} className="text-green-600" />
              ) : (
                <XCircle size={18} className="text-red-500" />
              )}
              <h2 className="text-sm font-semibold text-text-primary">
                {lastResult.success ? "Import Complete" : "Import Failed"}
              </h2>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
              {Object.entries(lastResult.summary).map(([key, value]) => (
                <div key={key}>
                  <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                    {key.replace(/([A-Z])/g, " $1").trim()}
                  </p>
                  <p className="mt-0.5 text-lg font-bold tabular-nums text-text-primary">{value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Set List */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-text-primary">Available Sets</h2>
            <Button variant="ghost" size="sm" onClick={selectAllUnimported}>
              Select All New
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setSelectedSets(new Set())}>
              Clear
            </Button>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="Search sets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 rounded-[var(--radius-md)] border border-border bg-bg-surface py-2 pl-9 pr-3 text-sm"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={32} className="animate-spin text-accent-cyan" />
          </div>
        ) : (
          <motion.div
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {filteredSets.map((set) => {
              const isSelected = selectedSets.has(set.id);
              return (
                <motion.div key={set.id} variants={staggerItem}>
                  <Card
                    hoverable
                    className={`cursor-pointer transition-all ${
                      isSelected
                        ? "ring-2 ring-accent-cyan"
                        : ""
                    }`}
                    onClick={() => toggleSet(set.id)}
                  >
                    <CardContent>
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-semibold text-text-primary truncate">
                            {set.name}
                          </h3>
                          <p className="mt-0.5 text-xs text-text-muted font-mono">{set.id}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {set.imported ? (
                            <Badge variant="success">Imported</Badge>
                          ) : (
                            <Badge variant="neutral">New</Badge>
                          )}
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSet(set.id)}
                            onClick={(e) => e.stopPropagation()}
                            className="h-4 w-4 rounded border-gray-300 text-accent-cyan"
                          />
                        </div>
                      </div>
                      <div className="mt-2 flex items-center gap-4 text-xs text-text-secondary">
                        <span>{set.cards} cards</span>
                        <span>{set.releaseDate}</span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </div>
    </div>
  );
}
