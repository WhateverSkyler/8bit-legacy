"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ShieldCheck, ShieldAlert, RefreshCw, CheckCircle2, XCircle, AlertTriangle, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

interface SafetyCheck {
  name: string;
  passed: boolean;
  detail: string;
  threshold?: string;
  current?: string;
}

interface AdsSafetyStatus {
  hardLimits: { maxDailySpend: number; lifetimeNoConvCeiling: number; rollingRoasFloor: number };
  current: {
    todayDate: string;
    dailySpend: number;
    lifetimeCost: number;
    lifetimeConversions: number;
    threeDayDays: Array<{ date: string; cost: number; conversions: number }>;
    daysOfData: number;
    rollingRoas: number | null;
  };
  checks: SafetyCheck[];
  circuitBreaker: { tripped: boolean; reason?: string; trippedAt?: string };
  computedAt: string;
}

function fmt(n: number, digits = 2): string { return n.toFixed(digits); }

export default function SafetyPage() {
  const { data, isLoading, refetch, isFetching } = useQuery<AdsSafetyStatus>({
    queryKey: ["ads-safety-status"],
    queryFn: async () => {
      const r = await fetch("/api/safety/ads-status", { cache: "no-store" });
      if (!r.ok) throw new Error("Failed to load safety status");
      return r.json();
    },
    refetchInterval: 60_000,
  });

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={32} className="animate-spin text-accent-cyan" />
      </div>
    );
  }

  const allPassed = data.checks.every(c => c.passed);
  const tripped = data.circuitBreaker.tripped;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Ad Safety"
        description="Hard fail-safes that auto-pause Google Ads if breached. Read-only view; trips happen via the scheduled job."
      >
        <Button variant="secondary" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Refresh
        </Button>
      </PageHeader>

      {/* Headline status */}
      <Card>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {tripped ? (
                <ShieldAlert size={40} className="text-red-500" />
              ) : allPassed ? (
                <ShieldCheck size={40} className="text-green-600" />
              ) : (
                <AlertTriangle size={40} className="text-orange-500" />
              )}
              <div>
                <h2 className="text-2xl font-bold text-text-primary">
                  {tripped ? "CIRCUIT BREAKER TRIPPED" : allPassed ? "All checks passing" : "Some checks failing"}
                </h2>
                <p className="text-sm text-text-secondary">
                  {tripped
                    ? data.circuitBreaker.reason ?? "Campaign auto-paused"
                    : "Google Ads is allowed to run"}
                  {data.circuitBreaker.trippedAt && ` (since ${new Date(data.circuitBreaker.trippedAt).toLocaleString()})`}
                </p>
              </div>
            </div>
            <Badge variant={tripped ? "error" : allPassed ? "success" : "neutral"}>
              {tripped ? "PAUSED" : allPassed ? "OK" : "WARN"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Hard limits summary */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardContent>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Daily spend cap</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">${fmt(data.hardLimits.maxDailySpend)}</p>
            <p className="mt-1 text-xs text-text-secondary">Today: ${fmt(data.current.dailySpend)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Lifetime no-conv ceiling</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">${fmt(data.hardLimits.lifetimeNoConvCeiling)}</p>
            <p className="mt-1 text-xs text-text-secondary">
              Lifetime: ${fmt(data.current.lifetimeCost)} / {data.current.lifetimeConversions} conv
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Rolling 3-day ROAS floor</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{data.hardLimits.rollingRoasFloor}%</p>
            <p className="mt-1 text-xs text-text-secondary">
              {data.current.daysOfData < 7
                ? `Deferred — ${data.current.daysOfData}/7 days of data`
                : `Current: ${data.current.rollingRoas !== null ? Math.round(data.current.rollingRoas) + "%" : "n/a"}`}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Per-check breakdown */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Active checks</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {data.checks.map(check => (
            <Card key={check.name}>
              <CardContent>
                <div className="flex items-start gap-3">
                  {check.passed ? (
                    <CheckCircle2 size={20} className="mt-0.5 shrink-0 text-green-600" />
                  ) : (
                    <XCircle size={20} className="mt-0.5 shrink-0 text-red-500" />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-text-primary">{check.name}</h3>
                      <Badge variant={check.passed ? "success" : "error"}>
                        {check.passed ? "Pass" : "Fail"}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-text-secondary">{check.detail}</p>
                    {(check.threshold || check.current) && (
                      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <p className="font-semibold uppercase tracking-wide text-text-muted">Threshold</p>
                          <p className="font-mono text-text-secondary">{check.threshold ?? "—"}</p>
                        </div>
                        <div>
                          <p className="font-semibold uppercase tracking-wide text-text-muted">Current</p>
                          <p className="font-mono text-text-secondary">{check.current ?? "—"}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Recent days */}
      {data.current.threeDayDays.length > 0 && (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-text-primary">Last 3 days</h2>
          <Card>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
                      <th className="px-3 py-2 text-left">Date</th>
                      <th className="px-3 py-2 text-right">Spend</th>
                      <th className="px-3 py-2 text-right">Conversions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.current.threeDayDays.map(d => (
                      <tr key={d.date} className="border-b border-border last:border-0">
                        <td className="px-3 py-2 text-text-primary">{d.date}</td>
                        <td className="px-3 py-2 text-right font-mono tabular-nums text-text-secondary">${fmt(d.cost)}</td>
                        <td className="px-3 py-2 text-right font-mono tabular-nums text-text-secondary">{d.conversions}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <p className="text-xs text-text-muted">
        Status computed at {new Date(data.computedAt).toLocaleString()}. Auto-refreshes every 60s.
        Active enforcement runs in the <code className="rounded bg-bg-surface px-1">ads-safety-check</code> scheduled job (every 6h).
      </p>
    </div>
  );
}
