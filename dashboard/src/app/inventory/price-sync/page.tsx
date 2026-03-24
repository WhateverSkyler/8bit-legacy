"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";
import { Upload, FileText, Check, AlertTriangle, Loader2, History } from "lucide-react";
import { useState, useRef, useCallback } from "react";
import { usePriceSyncUpload, usePriceSyncDiff, usePriceSyncApply, usePriceSyncHistory } from "@/hooks/use-price-sync";
import { formatCurrency } from "@/lib/utils";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import type { PriceDiffRecord, PriceChartingItem } from "@/types/product";

interface DiffReport {
  changes: PriceDiffRecord[];
  skippedProfit: PriceDiffRecord[];
  noChange: PriceDiffRecord[];
  unmatched: PriceChartingItem[];
  summary: {
    totalPcItems: number;
    matched: number;
    changesNeeded: number;
    belowProfit: number;
    noChangeNeeded: number;
    unmatchedCount: number;
  };
}

type TabId = "changes" | "below_profit" | "no_change" | "unmatched";

export default function PriceSyncPage() {
  const [activeTab, setActiveTab] = useState<TabId>("changes");
  const [diffReport, setDiffReport] = useState<DiffReport | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [fileName, setFileName] = useState("");
  const [applyResult, setApplyResult] = useState<{ success: number; failed: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const upload = usePriceSyncUpload();
  const diff = usePriceSyncDiff();
  const apply = usePriceSyncApply();
  const history = usePriceSyncHistory();

  const handleFile = useCallback(async (file: File) => {
    setFileName(file.name);
    setApplyResult(null);
    const csvText = await file.text();

    // Step 1: Parse CSV
    const parsed = await upload.mutateAsync(csvText);

    // Step 2: Generate diff
    const report = await diff.mutateAsync({ pcItems: parsed.items });
    setDiffReport(report);

    // Select all changes by default
    const ids = new Set<string>();
    for (const r of report.changes) {
      ids.add(r.variantId);
    }
    setSelectedIds(ids);
  }, [upload, diff]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) handleFile(file);
  }, [handleFile]);

  const handleBrowse = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const toggleSelect = (variantId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(variantId)) next.delete(variantId);
      else next.add(variantId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!diffReport) return;
    if (selectedIds.size === diffReport.changes.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(diffReport.changes.map((r) => r.variantId)));
    }
  };

  const handleApply = async () => {
    if (!diffReport) return;
    const changes = diffReport.changes
      .filter((r) => selectedIds.has(r.variantId))
      .map((r) => ({
        variantId: r.variantId,
        newPrice: r.newPrice,
        productTitle: r.productTitle,
        marketPrice: r.marketPrice,
        oldPrice: r.currentShopifyPrice,
        priceDiff: r.priceDiff,
        estimatedProfit: r.estimatedProfit,
      }));

    if (changes.length === 0) return;
    const result = await apply.mutateAsync(changes);
    setApplyResult(result);
  };

  const handleReset = () => {
    setDiffReport(null);
    setSelectedIds(new Set());
    setFileName("");
    setApplyResult(null);
    upload.reset();
    diff.reset();
    apply.reset();
  };

  const isLoading = upload.isPending || diff.isPending;
  const error = upload.error || diff.error;

  const tabs = diffReport
    ? [
        { id: "changes" as const, label: "Changes", count: diffReport.summary.changesNeeded },
        { id: "below_profit" as const, label: "Below Profit", count: diffReport.summary.belowProfit },
        { id: "no_change" as const, label: "No Change", count: diffReport.summary.noChangeNeeded },
        { id: "unmatched" as const, label: "Unmatched", count: diffReport.summary.unmatchedCount },
      ]
    : [];

  const currentRows: PriceDiffRecord[] =
    activeTab === "changes"
      ? diffReport?.changes ?? []
      : activeTab === "below_profit"
        ? diffReport?.skippedProfit ?? []
        : activeTab === "no_change"
          ? diffReport?.noChange ?? []
          : [];

  const currentUnmatched = activeTab === "unmatched" ? diffReport?.unmatched ?? [] : [];

  return (
    <div className="space-y-6">
      <PageHeader title="Price Sync" description="Upload PriceCharting CSV and sync to Shopify." />

      {/* Upload Area */}
      {!diffReport && !isLoading ? (
        <Card>
          <CardContent>
            <div
              className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border-2 border-dashed border-border bg-bg-nested p-12 transition-colors hover:border-accent-cyan/50 hover:bg-bg-hover/30 cursor-pointer"
              onClick={handleBrowse}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-cyan-glow mb-4">
                <Upload size={24} className="text-accent-cyan" />
              </div>
              <p className="text-sm font-semibold text-text-primary">
                Drop your PriceCharting CSV here
              </p>
              <p className="mt-1 text-xs text-text-secondary">
                or click to browse files
              </p>
              {error && (
                <div className="mt-4 flex items-center gap-2 text-status-error">
                  <AlertTriangle size={16} />
                  <p className="text-sm">{(error as Error).message}</p>
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={handleInputChange}
            />
          </CardContent>
        </Card>
      ) : isLoading ? (
        <Card>
          <CardContent>
            <div className="flex flex-col items-center justify-center p-12">
              <Loader2 size={32} className="animate-spin text-accent-cyan mb-4" />
              <p className="text-sm text-text-secondary">
                {upload.isPending ? "Parsing CSV..." : "Generating price diff..."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* File Info + Apply */}
          <Card>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-cyan-glow">
                    <FileText size={20} className="text-accent-cyan" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">{fileName}</p>
                    <p className="text-xs text-text-secondary">
                      {diffReport!.summary.totalPcItems} items loaded &middot; {diffReport!.summary.changesNeeded} price changes detected &middot; {diffReport!.summary.matched} matched
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="secondary" size="sm" onClick={handleReset}>
                    Upload New
                  </Button>
                  {applyResult ? (
                    <Badge variant={applyResult.failed === 0 ? "success" : "warning"}>
                      {applyResult.success} applied{applyResult.failed > 0 ? `, ${applyResult.failed} failed` : ""}
                    </Badge>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleApply}
                      disabled={selectedIds.size === 0 || apply.isPending}
                    >
                      {apply.isPending ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Check size={14} />
                      )}
                      Apply Selected ({selectedIds.size})
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tabs */}
          <Tabs tabs={tabs} activeTab={activeTab} onChange={(id) => setActiveTab(id as TabId)} />

          {/* Diff Table */}
          {activeTab !== "unmatched" ? (
            <Card>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b-2 border-border">
                        {activeTab === "changes" && (
                          <th className="px-4 py-3 text-left">
                            <input
                              type="checkbox"
                              checked={diffReport!.changes.length > 0 && selectedIds.size === diffReport!.changes.length}
                              onChange={toggleSelectAll}
                              className="rounded border-border"
                            />
                          </th>
                        )}
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Product</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Market</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Current</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">New</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Diff</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Profit</th>
                        <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Match</th>
                      </tr>
                    </thead>
                    <motion.tbody variants={staggerContainer} initial="hidden" animate="visible" key={activeTab}>
                      {currentRows.length === 0 ? (
                        <tr>
                          <td colSpan={activeTab === "changes" ? 8 : 7} className="px-4 py-8 text-center text-sm text-text-muted">
                            No items in this category.
                          </td>
                        </tr>
                      ) : (
                        currentRows.map((item) => (
                          <motion.tr
                            key={item.variantId}
                            variants={staggerItem}
                            className="border-b border-border hover:bg-bg-hover/50 transition-colors"
                          >
                            {activeTab === "changes" && (
                              <td className="px-4 py-3">
                                <input
                                  type="checkbox"
                                  checked={selectedIds.has(item.variantId)}
                                  onChange={() => toggleSelect(item.variantId)}
                                  className="rounded border-border"
                                />
                              </td>
                            )}
                            <td className="px-4 py-3">
                              <p className="text-sm font-medium text-text-primary">{item.productTitle}</p>
                              {item.console && <p className="text-xs text-text-muted">{item.console}</p>}
                            </td>
                            <td className="px-4 py-3 text-right text-sm tabular-nums text-text-secondary">
                              {formatCurrency(item.marketPrice)}
                            </td>
                            <td className="px-4 py-3 text-right text-sm tabular-nums text-text-secondary">
                              {formatCurrency(item.currentShopifyPrice)}
                            </td>
                            <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-text-primary">
                              {formatCurrency(item.newPrice)}
                            </td>
                            <td className={`px-4 py-3 text-right text-sm font-medium tabular-nums ${item.priceDiff >= 0 ? "text-status-success" : "text-status-error"}`}>
                              {item.priceDiff >= 0 ? "+" : ""}{formatCurrency(item.priceDiff)}
                            </td>
                            <td className={`px-4 py-3 text-right text-sm tabular-nums ${item.meetsMinProfit ? "text-text-primary" : "text-status-error"}`}>
                              {formatCurrency(item.estimatedProfit)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Badge variant="info">{item.matchType}</Badge>
                            </td>
                          </motion.tr>
                        ))
                      )}
                    </motion.tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : (
            /* Unmatched items */
            <Card>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b-2 border-border">
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">PriceCharting Name</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Console</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Loose Price</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">CIB Price</th>
                      </tr>
                    </thead>
                    <motion.tbody variants={staggerContainer} initial="hidden" animate="visible" key="unmatched">
                      {currentUnmatched.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-sm text-text-muted">
                            All items matched!
                          </td>
                        </tr>
                      ) : (
                        currentUnmatched.map((item, i) => (
                          <motion.tr
                            key={`${item.name}-${i}`}
                            variants={staggerItem}
                            className="border-b border-border hover:bg-bg-hover/50 transition-colors"
                          >
                            <td className="px-4 py-3 text-sm font-medium text-text-primary">{item.name}</td>
                            <td className="px-4 py-3 text-sm text-text-secondary">{item.console}</td>
                            <td className="px-4 py-3 text-right text-sm tabular-nums text-text-secondary">
                              {formatCurrency(item.loosePrice)}
                            </td>
                            <td className="px-4 py-3 text-right text-sm tabular-nums text-text-secondary">
                              {formatCurrency(item.cibPrice)}
                            </td>
                          </motion.tr>
                        ))
                      )}
                    </motion.tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Sync History */}
          {history.data?.runs && (
            <Card>
              <CardContent>
                <div className="flex items-center gap-2 mb-4">
                  <History size={16} className="text-text-muted" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted">Past Syncs</h3>
                </div>
                <div className="space-y-2">
                  {history.data.runs.map((run: { id: number; timestamp: string; totalItems: number; changesApplied: number; belowProfit: number; unmatched: number; netAdjustment: number }) => (
                    <div key={run.id} className="flex items-center justify-between rounded-[var(--radius-md)] bg-bg-nested p-3">
                      <div>
                        <p className="text-sm font-medium text-text-primary">
                          {new Date(run.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                        </p>
                        <p className="text-xs text-text-secondary">
                          {run.totalItems} items &middot; {run.changesApplied} changes &middot; {run.belowProfit} below profit &middot; {run.unmatched} unmatched
                        </p>
                      </div>
                      <span className={`text-sm font-semibold tabular-nums ${run.netAdjustment >= 0 ? "text-status-success" : "text-status-error"}`}>
                        {run.netAdjustment >= 0 ? "+" : ""}{formatCurrency(run.netAdjustment)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
