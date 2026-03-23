"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, Check } from "lucide-react";
import { useState } from "react";

const SYNC_TABS = [
  { id: "changes", label: "Changes", count: 12 },
  { id: "below_profit", label: "Below Profit", count: 3 },
  { id: "no_change", label: "No Change", count: 45 },
  { id: "unmatched", label: "Unmatched", count: 5 },
];

export default function PriceSyncPage() {
  const [activeTab, setActiveTab] = useState("changes");
  const [uploaded, setUploaded] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader title="Price Sync" description="Upload PriceCharting CSV and sync to Shopify." />

      {/* Upload Area */}
      {!uploaded ? (
        <Card>
          <CardContent>
            <div
              className="flex flex-col items-center justify-center rounded-[var(--radius-card)] border-2 border-dashed border-border bg-bg-nested p-12 transition-colors hover:border-accent-cyan/50 hover:bg-bg-hover/30 cursor-pointer"
              onClick={() => setUploaded(true)}
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
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* File Info */}
          <Card>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-cyan-glow">
                    <FileText size={20} className="text-accent-cyan" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">pricecharting-export.csv</p>
                    <p className="text-xs text-text-secondary">65 items loaded &middot; 12 price changes detected</p>
                  </div>
                </div>
                <Button variant="primary" size="sm">
                  <Check size={14} />
                  Apply Selected (12)
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Diff Report */}
          <Tabs tabs={SYNC_TABS} activeTab={activeTab} onChange={setActiveTab} />

          <Card>
            <CardContent>
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-border">
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Product</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Market</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Current</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">New</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Diff</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Profit</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Match</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: "Super Mario Bros 3", market: 25.92, current: 32.99, newPrice: 34.99, diff: 2.0, profit: 7.76, match: "title_exact" },
                    { name: "Pokemon Red", market: 37.03, current: 47.99, newPrice: 49.99, diff: 2.0, profit: 11.51, match: "upc" },
                    { name: "Sonic 2", market: 11.10, current: 13.99, newPrice: 14.99, diff: 1.0, profit: 3.46, match: "fuzzy" },
                  ].map((item) => (
                    <tr key={item.name} className="border-b border-border hover:bg-bg-hover/50 transition-colors">
                      <td className="px-4 py-3 text-sm font-medium text-text-primary">{item.name}</td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums text-text-secondary">${item.market.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums text-text-secondary">${item.current.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-text-primary">${item.newPrice.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right text-sm font-medium tabular-nums text-status-success">+${item.diff.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums text-text-primary">${item.profit.toFixed(2)}</td>
                      <td className="px-4 py-3 text-center"><Badge variant="info">{item.match}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
