"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Save, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { PricingConfig } from "@/types/pricing";

export default function SettingsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const resp = await fetch("/api/settings");
      if (!resp.ok) throw new Error("Failed to load settings");
      return resp.json() as Promise<{
        pricing: PricingConfig;
        connections: {
          shopify: { configured: boolean; storeUrl: string | null };
          ebay: { configured: boolean };
          googleAds: { configured: boolean };
          buffer: { configured: boolean };
        };
      }>;
    },
  });

  const saveMutation = useMutation({
    mutationFn: async (pricing: PricingConfig) => {
      const resp = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pricing }),
      });
      if (!resp.ok) throw new Error("Failed to save settings");
      return resp.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    },
  });

  const [multiplier, setMultiplier] = useState("1.35");
  const [minProfit, setMinProfit] = useState("3.00");
  const [roundTo, setRoundTo] = useState("0.99");
  const [feePercent, setFeePercent] = useState("2.9");
  const [feeFixed, setFeeFixed] = useState("0.30");
  const [priceField, setPriceField] = useState("loose");
  const [categoryMultipliers, setCategoryMultipliers] = useState<Record<string, string>>({});
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [autoApply, setAutoApply] = useState(false);
  const [autoApplyThreshold, setAutoApplyThreshold] = useState("15");
  const [maxPriceChange, setMaxPriceChange] = useState("30");
  const [factorAdSpend, setFactorAdSpend] = useState(false);

  // Populate form when data loads
  useEffect(() => {
    if (data?.pricing) {
      const p = data.pricing;
      setMultiplier(p.default_multiplier.toString());
      setMinProfit(p.minimum_profit_usd.toString());
      setRoundTo(p.round_to?.toString() ?? "");
      setFeePercent((p.shopify_fee_percent * 100).toString());
      setFeeFixed(p.shopify_fee_fixed.toString());
      setPriceField(p.price_field);
      const cats: Record<string, string> = {};
      for (const [k, v] of Object.entries(p.category_multipliers)) {
        cats[k] = v.toString();
      }
      setCategoryMultipliers(cats);
      setAutoApply(p.auto_apply_enabled ?? false);
      setAutoApplyThreshold((p.auto_apply_threshold_percent ?? 15).toString());
      setMaxPriceChange((p.max_price_change_percent ?? 30).toString());
      setFactorAdSpend(p.factor_ad_spend ?? false);
    }
  }, [data]);

  const handleSave = () => {
    const catMults: Record<string, number> = {};
    for (const [k, v] of Object.entries(categoryMultipliers)) {
      catMults[k] = parseFloat(v) || 1.35;
    }

    const pricing: PricingConfig = {
      default_multiplier: parseFloat(multiplier) || 1.35,
      minimum_profit_usd: parseFloat(minProfit) || 3.0,
      shopify_fee_percent: (parseFloat(feePercent) || 2.9) / 100,
      shopify_fee_fixed: parseFloat(feeFixed) || 0.3,
      price_field: priceField as "loose" | "cib" | "new",
      round_to: roundTo ? parseFloat(roundTo) : null,
      category_multipliers: catMults,
      auto_apply_enabled: autoApply,
      auto_apply_threshold_percent: parseInt(autoApplyThreshold) || 15,
      max_price_change_percent: parseInt(maxPriceChange) || 30,
      factor_ad_spend: factorAdSpend,
    };

    saveMutation.mutate(pricing);
  };

  const connections = data?.connections;
  const apiList = [
    { name: "Shopify Admin API", connected: connections?.shopify.configured ?? false, hint: connections?.shopify.storeUrl || "Not configured" },
    { name: "eBay Browse API", connected: connections?.ebay.configured ?? false, hint: connections?.ebay.configured ? "Connected" : "Not configured" },
    { name: "Google Ads API", connected: connections?.googleAds.configured ?? false, hint: connections?.googleAds.configured ? "Connected" : "Not configured" },
    { name: "Buffer API", connected: connections?.buffer.configured ?? false, hint: connections?.buffer.configured ? "Connected" : "Not configured" },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={32} className="animate-spin text-accent-cyan" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="API keys, pricing rules, and configuration.">
        <div className="flex items-center gap-2">
          {saveSuccess && <Badge variant="success">Saved!</Badge>}
          <Button variant="primary" size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </Button>
        </div>
      </PageHeader>

      {/* API Connections */}
      <Card>
        <CardContent>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">API Connections</h3>
          <div className="space-y-3">
            {apiList.map((api) => (
              <div key={api.name} className="flex items-center justify-between rounded-[var(--radius-md)] bg-bg-nested p-4">
                <div className="flex items-center gap-3">
                  {api.connected ? (
                    <CheckCircle size={18} className="text-status-success" />
                  ) : (
                    <XCircle size={18} className="text-text-muted" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-text-primary">{api.name}</p>
                    <p className="text-xs text-text-muted">{api.hint}</p>
                  </div>
                </div>
                <Badge variant={api.connected ? "success" : "neutral"}>
                  {api.connected ? "Connected" : "Not Set"}
                </Badge>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-text-muted">
            API keys are set in <code className="bg-bg-nested px-1 py-0.5 rounded text-accent-cyan">dashboard/.env.local</code>
          </p>
        </CardContent>
      </Card>

      {/* Pricing Rules */}
      <Card>
        <CardContent>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Pricing Rules</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Default Multiplier</label>
              <Input type="number" step="0.01" value={multiplier} onChange={(e) => setMultiplier(e.target.value)} />
              <p className="mt-1 text-xs text-text-muted">Market price x {multiplier}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Min Profit ($)</label>
              <Input type="number" step="0.50" value={minProfit} onChange={(e) => setMinProfit(e.target.value)} />
              <p className="mt-1 text-xs text-text-muted">Items below this get flagged</p>
            </div>
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Round To</label>
              <Input type="number" step="0.01" value={roundTo} onChange={(e) => setRoundTo(e.target.value)} placeholder="e.g. 0.99" />
              <p className="mt-1 text-xs text-text-muted">Prices end in .{roundTo ? roundTo.split(".")[1] || "99" : "xx"}</p>
            </div>
          </div>

          <div className="mt-4">
            <label className="text-xs font-medium text-text-secondary mb-1 block">Price Field</label>
            <div className="flex gap-2">
              {(["loose", "cib", "new"] as const).map((field) => (
                <button
                  key={field}
                  onClick={() => setPriceField(field)}
                  className={`rounded-[var(--radius-md)] border px-4 py-2 text-sm font-medium transition-colors ${
                    priceField === field
                      ? "border-accent-cyan bg-cyan-glow text-accent-cyan"
                      : "border-border bg-bg-nested text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {field.charAt(0).toUpperCase() + field.slice(1)}
                </button>
              ))}
            </div>
            <p className="mt-1 text-xs text-text-muted">Which PriceCharting price to use for syncing</p>
          </div>

          <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted mt-6 mb-3">Category Multipliers</h4>
          <div className="space-y-2">
            {Object.entries(categoryMultipliers).map(([category, value]) => (
              <div key={category} className="flex items-center gap-3 rounded-[var(--radius-md)] bg-bg-nested p-3">
                <span className="flex-1 text-sm text-text-primary capitalize">{category.replace(/_/g, " ")}</span>
                <Input
                  type="number"
                  step="0.01"
                  value={value}
                  onChange={(e) => setCategoryMultipliers((prev) => ({ ...prev, [category]: e.target.value }))}
                  className="w-24"
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Shopify Fees */}
      <Card>
        <CardContent>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Shopify Fees</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Transaction Fee (%)</label>
              <Input type="number" step="0.1" value={feePercent} onChange={(e) => setFeePercent(e.target.value)} />
            </div>
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Fixed Fee ($)</label>
              <Input type="number" step="0.01" value={feeFixed} onChange={(e) => setFeeFixed(e.target.value)} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Automation Controls */}
      <Card>
        <CardContent>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Pricing Automation</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-[var(--radius-md)] bg-bg-nested p-4">
              <div>
                <p className="text-sm font-medium text-text-primary">Auto-apply price changes</p>
                <p className="text-xs text-text-muted">Automatically update Shopify prices from PriceCharting data</p>
              </div>
              <button
                onClick={() => setAutoApply(!autoApply)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  autoApply ? "bg-accent-cyan" : "bg-border"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    autoApply ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="text-xs font-medium text-text-secondary mb-1 block">Auto-apply threshold (%)</label>
                <Input
                  type="number"
                  step="1"
                  value={autoApplyThreshold}
                  onChange={(e) => setAutoApplyThreshold(e.target.value)}
                />
                <p className="mt-1 text-xs text-text-muted">Changes above this % need manual review</p>
              </div>
              <div>
                <label className="text-xs font-medium text-text-secondary mb-1 block">Max price change (%)</label>
                <Input
                  type="number"
                  step="1"
                  value={maxPriceChange}
                  onChange={(e) => setMaxPriceChange(e.target.value)}
                />
                <p className="mt-1 text-xs text-text-muted">Hard limit — changes above this are rejected</p>
              </div>
            </div>

            <div className="flex items-center justify-between rounded-[var(--radius-md)] bg-bg-nested p-4">
              <div>
                <p className="text-sm font-medium text-text-primary">Factor in ad spend</p>
                <p className="text-xs text-text-muted">Include Google Ads cost-per-order in profit calculations</p>
              </div>
              <button
                onClick={() => setFactorAdSpend(!factorAdSpend)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  factorAdSpend ? "bg-accent-cyan" : "bg-border"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    factorAdSpend ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {saveMutation.isError && (
        <p className="text-center text-sm text-status-error">
          Failed to save: {(saveMutation.error as Error).message}
        </p>
      )}
    </div>
  );
}
