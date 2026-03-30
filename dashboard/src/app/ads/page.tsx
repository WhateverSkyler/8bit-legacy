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
  PauseCircle,
} from "lucide-react";
import { useState } from "react";
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

export default function AdsPage() {
  const [activeTab, setActiveTab] = useState("overview");

  const { data: perfData, isLoading } = useAdsPerformance();
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
  };
  const daily = perfData?.daily ?? [];
  const terms = termsData?.terms ?? [];
  const actions = actionsData?.actions ?? [];

  const TABS = [
    { id: "overview", label: "Overview" },
    { id: "search-terms", label: "Search Terms", count: terms.filter((t: any) => t.suggestedAction === "add_negative").length || undefined },
    { id: "actions", label: "Actions Log", count: actions.length || undefined },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Google Ads" description="Campaign performance and autonomous optimization.">
        <div className="flex items-center gap-2">
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

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Spend vs Revenue Chart */}
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

      {/* Search Terms Tab */}
      {activeTab === "search-terms" && (
        <Card>
          <CardContent>
            {terms.length === 0 ? (
              <p className="text-center text-sm text-text-muted py-8">
                No search term data. Sync Google Ads data first.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-border">
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Search Term</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Clicks</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Cost</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Conversions</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Suggestion</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Action</th>
                    </tr>
                  </thead>
                  <motion.tbody variants={staggerContainer} initial="hidden" animate="visible">
                    {terms.map((term: any, i: number) => (
                      <motion.tr key={i} variants={staggerItem} className="border-b border-border hover:bg-bg-hover/50">
                        <td className="px-4 py-3 text-sm text-text-primary">{term.searchTerm}</td>
                        <td className="px-4 py-3 text-right text-sm tabular-nums">{term.clicks}</td>
                        <td className="px-4 py-3 text-right text-sm tabular-nums">{formatCurrency(term.cost)}</td>
                        <td className="px-4 py-3 text-right text-sm tabular-nums">{term.conversions}</td>
                        <td className="px-4 py-3 text-center">
                          <Badge
                            variant={
                              term.suggestedAction === "keep" ? "success" :
                              term.suggestedAction === "add_negative" ? "error" : "neutral"
                            }
                          >
                            {term.suggestedAction === "add_negative" ? "Negate" : term.suggestedAction}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {term.suggestedAction === "add_negative" && !term.isNegative && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                executeAction.mutate({
                                  actionType: "add_negative_keyword",
                                  targetEntityType: "search_term",
                                  targetEntityId: term.campaignId,
                                  targetEntityName: term.searchTerm,
                                  reason: `${term.clicks} clicks, 0 conversions`,
                                })
                              }
                            >
                              <MinusCircle size={14} />
                              Negate
                            </Button>
                          )}
                          {term.isNegative && (
                            <span className="text-xs text-text-muted">Negated</span>
                          )}
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

      {/* Actions Log Tab */}
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
