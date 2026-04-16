"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency } from "@/lib/utils";
import {
  Loader2,
  RefreshCw,
  Zap,
  DollarSign,
  TrendingUp,
  MousePointerClick,
  Target,
  MinusCircle,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Eye,
  ArrowUpDown,
} from "lucide-react";
import { useState, useMemo } from "react";
import {
  useAdsPerformance,
  useAdsSearchTerms,
  useAdsSyncData,
  useAdsOptimize,
  useAdsActions,
  useExecuteAdAction,
} from "@/hooks/use-google-ads";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

type SortField = "clicks" | "cost" | "impressions" | "conversions" | "roas" | "cpc" | "ctr";
type SortDir = "asc" | "desc";

export default function AdsPage() {
  const [activeTab, setActiveTab] = useState("health");
  const [selectedTerms, setSelectedTerms] = useState<Set<string>>(new Set());
  const [productSort, setProductSort] = useState<{ field: SortField; dir: SortDir }>({ field: "cost", dir: "desc" });

  const { data: perfData, isLoading } = useAdsPerformance();
  const { data: productPerfData } = useAdsPerformance({ entityType: "product" });
  const { data: termsData } = useAdsSearchTerms();
  const { data: actionsData } = useAdsActions();
  const syncMutation = useAdsSyncData();
  const optimizeMutation = useAdsOptimize();
  const executeAction = useExecuteAdAction();

  const summary = perfData?.summary ?? {
    totalSpend: 0,
    totalRevenue: 0,
    roas: 0,
    avgCpc: 0,
    totalClicks: 0,
    totalConversions: 0,
    totalImpressions: 0,
  };
  const promoCredit = perfData?.promoCredit ?? {
    total: 700,
    spent: 0,
    remaining: 700,
    expiryDate: "2026-05-31",
    daysUntilExpiry: 45,
    requiredDailySpend: 15.56,
    avgDailySpend: 0,
    onTrack: false,
  };
  const rolling3dRoas = perfData?.rolling3dRoas ?? 0;
  const circuitBreakers = perfData?.circuitBreakers ?? { google_ads: { tripped: false } };
  const daily = perfData?.daily ?? [];
  const terms = termsData?.terms ?? [];
  const actions = actionsData?.actions ?? [];
  const productEntities = productPerfData?.entities ?? [];

  // Sort products
  const sortedProducts = useMemo(() => {
    const items = [...productEntities];
    items.sort((a: any, b: any) => {
      let aVal: number, bVal: number;
      switch (productSort.field) {
        case "clicks": aVal = a.clicks; bVal = b.clicks; break;
        case "cost": aVal = a.cost; bVal = b.cost; break;
        case "impressions": aVal = a.impressions; bVal = b.impressions; break;
        case "conversions": aVal = a.conversions; bVal = b.conversions; break;
        case "roas": aVal = a.roas; bVal = b.roas; break;
        case "cpc": aVal = a.cpc; bVal = b.cpc; break;
        case "ctr":
          aVal = a.impressions > 0 ? a.clicks / a.impressions : 0;
          bVal = b.impressions > 0 ? b.clicks / b.impressions : 0;
          break;
        default: aVal = a.cost; bVal = b.cost;
      }
      return productSort.dir === "desc" ? bVal - aVal : aVal - bVal;
    });
    return items;
  }, [productEntities, productSort]);

  const toggleProductSort = (field: SortField) => {
    setProductSort(prev =>
      prev.field === field
        ? { field, dir: prev.dir === "desc" ? "asc" : "desc" }
        : { field, dir: "desc" }
    );
  };

  // Search terms sorted by cost desc (biggest waste first)
  const sortedTerms = useMemo(() => {
    return [...terms].sort((a: any, b: any) => b.cost - a.cost);
  }, [terms]);

  const toggleTermSelection = (searchTerm: string) => {
    setSelectedTerms(prev => {
      const next = new Set(prev);
      if (next.has(searchTerm)) next.delete(searchTerm);
      else next.add(searchTerm);
      return next;
    });
  };

  const negateSelected = () => {
    for (const term of selectedTerms) {
      const t = terms.find((t: any) => t.searchTerm === term);
      if (t && !t.isNegative) {
        executeAction.mutate({
          actionType: "add_negative_keyword",
          targetEntityType: "search_term",
          targetEntityId: t.campaignId,
          targetEntityName: t.searchTerm,
          reason: `Bulk negate: ${t.clicks} clicks, 0 conversions`,
        });
      }
    }
    setSelectedTerms(new Set());
  };

  const TABS = [
    { id: "health", label: "Campaign Health" },
    { id: "overview", label: "Overview" },
    { id: "products", label: "Products", count: productEntities.length || undefined },
    { id: "search-terms", label: "Search Terms", count: terms.filter((t: any) => t.suggestedAction === "add_negative").length || undefined },
    { id: "actions", label: "Actions Log", count: actions.length || undefined },
  ];

  const adsBreaker = circuitBreakers.google_ads ?? { tripped: false };

  return (
    <div className="space-y-6">
      <PageHeader title="Google Ads" description="Standard Shopping campaign — high-intent search capture.">
        <div className="flex items-center gap-2">
          {adsBreaker.tripped && (
            <Badge variant="error">Circuit Breaker TRIPPED</Badge>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Sync Data
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => optimizeMutation.mutate()}
            disabled={optimizeMutation.isPending}
          >
            {optimizeMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            Run Optimization
          </Button>
        </div>
      </PageHeader>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-red-100 p-2">
                <DollarSign size={20} className="text-red-500" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Spend (30d)</p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">{formatCurrency(summary.totalSpend)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-green-100 p-2">
                <TrendingUp size={20} className="text-green-500" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Revenue (30d)</p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">{formatCurrency(summary.totalRevenue)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-cyan-100 p-2">
                <Target size={20} className="text-cyan-600" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">ROAS</p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">{summary.roas}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-purple-100 p-2">
                <MousePointerClick size={20} className="text-purple-500" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Avg CPC</p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">{formatCurrency(summary.avgCpc)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      {/* ── Campaign Health Tab ── */}
      {activeTab === "health" && (
        <div className="space-y-6">
          {/* Promo Credit Burn Tracker */}
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">
                Promo Credit — ${promoCredit.total} (expires {promoCredit.expiryDate})
              </h3>
              <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
                <div>
                  <p className="text-xs text-text-muted">Spent</p>
                  <p className="text-xl font-bold tabular-nums">{formatCurrency(promoCredit.spent)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Remaining</p>
                  <p className="text-xl font-bold tabular-nums text-orange-600">{formatCurrency(promoCredit.remaining)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Days Left</p>
                  <p className="text-xl font-bold tabular-nums">{promoCredit.daysUntilExpiry}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Need/Day</p>
                  <p className="text-xl font-bold tabular-nums">{formatCurrency(promoCredit.requiredDailySpend)}</p>
                </div>
              </div>
              {/* Progress bar */}
              <div className="mt-4">
                <div className="flex justify-between text-xs text-text-muted mb-1">
                  <span>Credit used: {Math.round((promoCredit.spent / promoCredit.total) * 100)}%</span>
                  <span>{formatCurrency(promoCredit.spent)} / {formatCurrency(promoCredit.total)}</span>
                </div>
                <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${promoCredit.onTrack ? "bg-green-500" : "bg-orange-500"}`}
                    style={{ width: `${Math.min(100, (promoCredit.spent / promoCredit.total) * 100)}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs mt-1">
                  <span className={promoCredit.onTrack ? "text-green-600" : "text-orange-600"}>
                    {promoCredit.onTrack ? "On track" : "Under-spending"} — avg {formatCurrency(promoCredit.avgDailySpend)}/day
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Safety + ROAS Cards */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Circuit Breaker */}
            <Card>
              <CardContent>
                <div className="flex items-center gap-3 mb-3">
                  {adsBreaker.tripped ? (
                    <ShieldAlert size={24} className="text-red-500" />
                  ) : (
                    <ShieldCheck size={24} className="text-green-500" />
                  )}
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Circuit Breaker</p>
                    <p className={`text-lg font-bold ${adsBreaker.tripped ? "text-red-600" : "text-green-600"}`}>
                      {adsBreaker.tripped ? "TRIPPED" : "Armed"}
                    </p>
                  </div>
                </div>
                {adsBreaker.tripped && (
                  <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm">
                    <p className="font-medium text-red-800">{adsBreaker.reason}</p>
                    <p className="text-xs text-red-600 mt-1">
                      Tripped: {adsBreaker.trippedAt ? new Date(adsBreaker.trippedAt).toLocaleString() : "Unknown"}
                    </p>
                  </div>
                )}
                {!adsBreaker.tripped && (
                  <p className="text-xs text-text-muted">
                    Auto-trips on: $25+ daily spend, 3 days no conversions, store downtime, ROAS below 200%
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Rolling 3-Day ROAS */}
            <Card>
              <CardContent>
                <div className="flex items-center gap-3 mb-3">
                  <TrendingUp size={24} className={rolling3dRoas >= 440 ? "text-green-500" : rolling3dRoas >= 200 ? "text-yellow-500" : "text-red-500"} />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Rolling 3-Day ROAS</p>
                    <p className={`text-2xl font-bold tabular-nums ${rolling3dRoas >= 440 ? "text-green-600" : rolling3dRoas >= 200 ? "text-yellow-600" : "text-red-600"}`}>
                      {rolling3dRoas}%
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 text-xs">
                  <Badge variant={rolling3dRoas >= 440 ? "success" : "neutral"}>440%+ = profitable</Badge>
                  <Badge variant={rolling3dRoas < 200 ? "error" : "neutral"}>{"<"}200% = trip</Badge>
                </div>
              </CardContent>
            </Card>

            {/* Conversion Funnel */}
            <Card>
              <CardContent>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted mb-3">30-Day Funnel</p>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-text-secondary flex items-center gap-1"><Eye size={14} /> Impressions</span>
                    <span className="text-sm font-medium tabular-nums">{(summary.totalImpressions ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-text-secondary flex items-center gap-1"><MousePointerClick size={14} /> Clicks</span>
                    <span className="text-sm font-medium tabular-nums">{summary.totalClicks.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-text-secondary flex items-center gap-1"><Target size={14} /> Conversions</span>
                    <span className="text-sm font-medium tabular-nums">{summary.totalConversions}</span>
                  </div>
                  {summary.totalImpressions > 0 && (
                    <div className="pt-2 border-t border-border text-xs text-text-muted">
                      CTR: {((summary.totalClicks / (summary.totalImpressions || 1)) * 100).toFixed(2)}%
                      {" | "}CVR: {summary.totalClicks > 0 ? ((summary.totalConversions / summary.totalClicks) * 100).toFixed(2) : "0.00"}%
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {perfData?.source === "sample" && (
            <p className="text-center text-xs text-text-muted">
              Showing sample data. Connect Google Ads API for real metrics.
            </p>
          )}
        </div>
      )}

      {/* ── Overview Tab ── */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Spend vs Revenue (30 Days)</h3>
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 size={24} className="animate-spin text-accent-cyan" />
                </div>
              ) : daily.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={daily}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                      tickFormatter={(v) => new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    />
                    <YAxis tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--color-bg-surface)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                        fontSize: 12,
                      }}
                      formatter={(value) => formatCurrency(Number(value))}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="spend" stroke="#ef4444" strokeWidth={2} dot={false} name="Spend" />
                    <Line type="monotone" dataKey="revenue" stroke="#22c55e" strokeWidth={2} dot={false} name="Revenue" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-sm text-text-muted py-8">
                  No data yet. Click &quot;Sync Data&quot; to pull from Google Ads.
                </p>
              )}
            </CardContent>
          </Card>

          {perfData?.source === "sample" && (
            <p className="text-center text-xs text-text-muted">
              Showing sample data. Connect Google Ads API for real metrics.
            </p>
          )}
        </div>
      )}

      {/* ── Products Tab ── */}
      {activeTab === "products" && (
        <Card>
          <CardContent>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted">
                Product Performance (30 Days)
              </h3>
              <p className="text-xs text-text-muted">{productEntities.length} products with traffic</p>
            </div>
            {productEntities.length === 0 ? (
              <p className="text-center text-sm text-text-muted py-8">
                No product performance data. Sync Google Ads data first.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-border">
                      <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted max-w-[250px]">Product</th>
                      {(["impressions", "clicks", "ctr", "cost", "cpc", "conversions", "roas"] as SortField[]).map((field) => (
                        <th
                          key={field}
                          className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted cursor-pointer hover:text-text-primary"
                          onClick={() => toggleProductSort(field)}
                        >
                          <span className="inline-flex items-center gap-1">
                            {field.toUpperCase()}
                            {productSort.field === field && (
                              <ArrowUpDown size={12} className="text-accent-cyan" />
                            )}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <motion.tbody variants={staggerContainer} initial="hidden" animate="visible">
                    {sortedProducts.slice(0, 50).map((product: any, i: number) => {
                      const ctr = product.impressions > 0 ? (product.clicks / product.impressions) * 100 : 0;
                      const rowColor = product.conversions > 0
                        ? "bg-green-50/50"
                        : product.clicks >= 20
                        ? "bg-red-50/50"
                        : "";
                      return (
                        <motion.tr key={i} variants={staggerItem} className={`border-b border-border hover:bg-bg-hover/50 ${rowColor}`}>
                          <td className="px-3 py-3 text-sm text-text-primary max-w-[250px] truncate" title={product.entityName}>
                            {product.entityName}
                          </td>
                          <td className="px-3 py-3 text-right text-sm tabular-nums">{product.impressions.toLocaleString()}</td>
                          <td className="px-3 py-3 text-right text-sm tabular-nums">{product.clicks}</td>
                          <td className="px-3 py-3 text-right text-sm tabular-nums">{ctr.toFixed(1)}%</td>
                          <td className="px-3 py-3 text-right text-sm tabular-nums">{formatCurrency(product.cost)}</td>
                          <td className="px-3 py-3 text-right text-sm tabular-nums">{formatCurrency(product.cpc)}</td>
                          <td className="px-3 py-3 text-right text-sm tabular-nums">
                            {product.conversions > 0 ? (
                              <span className="font-medium text-green-600">{product.conversions}</span>
                            ) : (
                              <span className="text-text-muted">0</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-right text-sm tabular-nums">
                            {product.roas > 0 ? (
                              <Badge variant={product.roas >= 4.4 ? "success" : product.roas >= 2 ? "warning" : "error"}>
                                {(product.roas * 100).toFixed(0)}%
                              </Badge>
                            ) : (
                              <span className="text-text-muted">—</span>
                            )}
                          </td>
                        </motion.tr>
                      );
                    })}
                  </motion.tbody>
                </table>
                {sortedProducts.length > 50 && (
                  <p className="text-center text-xs text-text-muted py-3">
                    Showing top 50 of {sortedProducts.length} products
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Search Terms Tab (Upgraded) ── */}
      {activeTab === "search-terms" && (
        <Card>
          <CardContent>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted">
                Search Terms — sorted by cost (biggest spend first)
              </h3>
              {selectedTerms.size > 0 && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={negateSelected}
                  disabled={executeAction.isPending}
                >
                  <MinusCircle size={14} />
                  Negate Selected ({selectedTerms.size})
                </Button>
              )}
            </div>
            {sortedTerms.length === 0 ? (
              <p className="text-center text-sm text-text-muted py-8">
                No search term data. Sync Google Ads data first.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-border">
                      <th className="px-2 py-3 text-center w-10">
                        <input
                          type="checkbox"
                          className="rounded"
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedTerms(new Set(
                                sortedTerms
                                  .filter((t: any) => t.suggestedAction === "add_negative" && !t.isNegative)
                                  .map((t: any) => t.searchTerm)
                              ));
                            } else {
                              setSelectedTerms(new Set());
                            }
                          }}
                        />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Search Term</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Clicks</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Cost</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Conversions</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Status</th>
                    </tr>
                  </thead>
                  <motion.tbody variants={staggerContainer} initial="hidden" animate="visible">
                    {sortedTerms.map((term: any, i: number) => {
                      const rowColor = term.conversions > 0
                        ? "bg-green-50/50"
                        : term.clicks >= 5 && term.conversions === 0
                        ? "bg-red-50/50"
                        : "";
                      return (
                        <motion.tr key={i} variants={staggerItem} className={`border-b border-border hover:bg-bg-hover/50 ${rowColor}`}>
                          <td className="px-2 py-3 text-center">
                            {term.suggestedAction === "add_negative" && !term.isNegative && (
                              <input
                                type="checkbox"
                                className="rounded"
                                checked={selectedTerms.has(term.searchTerm)}
                                onChange={() => toggleTermSelection(term.searchTerm)}
                              />
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-text-primary">{term.searchTerm}</td>
                          <td className="px-4 py-3 text-right text-sm tabular-nums">{term.clicks}</td>
                          <td className="px-4 py-3 text-right text-sm tabular-nums">{formatCurrency(term.cost)}</td>
                          <td className="px-4 py-3 text-right text-sm tabular-nums">
                            {term.conversions > 0 ? (
                              <span className="font-medium text-green-600">{term.conversions}</span>
                            ) : (
                              "0"
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {term.isNegative ? (
                              <Badge variant="neutral">Negated</Badge>
                            ) : term.conversions > 0 ? (
                              <Badge variant="success">Converting</Badge>
                            ) : term.suggestedAction === "add_negative" ? (
                              <Badge variant="error">Waste</Badge>
                            ) : (
                              <Badge variant="neutral">Watching</Badge>
                            )}
                          </td>
                        </motion.tr>
                      );
                    })}
                  </motion.tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Actions Log Tab ── */}
      {activeTab === "actions" && (
        <Card>
          <CardContent>
            {actions.length === 0 ? (
              <p className="text-center text-sm text-text-muted py-8">
                No automated actions yet. Run optimization to generate actions.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-border">
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Time</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Target</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Reason</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Status</th>
                    </tr>
                  </thead>
                  <motion.tbody variants={staggerContainer} initial="hidden" animate="visible">
                    {actions.map((action: any) => (
                      <motion.tr key={action.id} variants={staggerItem} className="border-b border-border hover:bg-bg-hover/50">
                        <td className="px-4 py-3 text-xs text-text-muted whitespace-nowrap">
                          {new Date(action.executedAt).toLocaleString("en-US", {
                            month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
                          })}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              action.actionType.includes("pause") ? "warning" :
                              action.actionType.includes("negative") ? "error" :
                              action.actionType.includes("increase") ? "success" : "info"
                            }
                          >
                            {action.actionType.replace(/_/g, " ")}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm text-text-primary max-w-[200px] truncate">{action.targetEntityName}</td>
                        <td className="px-4 py-3 text-xs text-text-secondary max-w-[250px] truncate">{action.reason}</td>
                        <td className="px-4 py-3 text-center">
                          <Badge variant={action.success ? "success" : "error"}>
                            {action.success ? "Done" : "Failed"}
                          </Badge>
                        </td>
                      </motion.tr>
                    ))}
                  </motion.tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
