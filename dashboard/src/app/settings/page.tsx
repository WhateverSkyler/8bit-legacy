"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Toggle } from "@/components/ui/toggle";
import { Badge } from "@/components/ui/badge";
import { Save, CheckCircle, XCircle } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  const [multiplier, setMultiplier] = useState("1.35");
  const [minProfit, setMinProfit] = useState("3.00");
  const [roundTo, setRoundTo] = useState("0.99");

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="API keys, pricing rules, and configuration.">
        <Button variant="primary" size="sm">
          <Save size={14} />
          Save Changes
        </Button>
      </PageHeader>

      {/* API Connections */}
      <Card>
        <CardContent>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">API Connections</h3>
          <div className="space-y-3">
            {[
              { name: "Shopify Admin API", connected: true, hint: "shpat_****" },
              { name: "eBay Browse API", connected: false, hint: "Not configured" },
              { name: "Google Ads API", connected: false, hint: "Not configured" },
              { name: "Buffer API", connected: false, hint: "Not configured" },
            ].map((api) => (
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
                <Button variant={api.connected ? "secondary" : "primary"} size="sm">
                  {api.connected ? "Test" : "Connect"}
                </Button>
              </div>
            ))}
          </div>
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
              <Input type="number" step="0.01" value={roundTo} onChange={(e) => setRoundTo(e.target.value)} />
              <p className="mt-1 text-xs text-text-muted">Prices end in .{roundTo.split(".")[1] || "99"}</p>
            </div>
          </div>

          <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted mt-6 mb-3">Category Multipliers</h4>
          <div className="space-y-2">
            {[
              { category: "Retro Games", multiplier: 1.35 },
              { category: "Pokemon Cards", multiplier: 1.35 },
              { category: "Consoles", multiplier: 1.30 },
              { category: "Accessories", multiplier: 1.40 },
            ].map((cat) => (
              <div key={cat.category} className="flex items-center gap-3 rounded-[var(--radius-md)] bg-bg-nested p-3">
                <span className="flex-1 text-sm text-text-primary">{cat.category}</span>
                <Input type="number" step="0.01" defaultValue={cat.multiplier.toString()} className="w-24" />
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
              <Input type="number" step="0.1" defaultValue="2.9" />
            </div>
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Fixed Fee ($)</label>
              <Input type="number" step="0.01" defaultValue="0.30" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
