"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency, formatDate } from "@/lib/utils";
import { RefreshCw, ExternalLink } from "lucide-react";
import { useState } from "react";

const SAMPLE_ORDERS = [
  { id: "#1042", date: "2026-03-23", customer: "Alex M.", city: "Atlanta, GA", items: "Super Mario Bros 3 (NES)", total: 34.99, status: "unfulfilled" as const },
  { id: "#1041", date: "2026-03-23", customer: "Sarah K.", city: "Portland, OR", items: "Pokemon Red (GB)", total: 49.99, status: "unfulfilled" as const },
  { id: "#1040", date: "2026-03-22", customer: "Mike R.", city: "Chicago, IL", items: "GoldenEye 007 (N64)", total: 29.99, status: "fulfilled" as const },
  { id: "#1039", date: "2026-03-22", customer: "Lisa P.", city: "Denver, CO", items: "Sonic 2 (Genesis)", total: 14.99, status: "fulfilled" as const },
  { id: "#1038", date: "2026-03-21", customer: "James T.", city: "Miami, FL", items: "Final Fantasy VII (PS1)", total: 39.99, status: "fulfilled" as const },
  { id: "#1037", date: "2026-03-20", customer: "Emma D.", city: "Seattle, WA", items: "Mega Man 2 (NES)", total: 24.99, status: "fulfilled" as const },
  { id: "#1036", date: "2026-03-19", customer: "Chris B.", city: "Austin, TX", items: "Zelda: Link to the Past (SNES)", total: 44.99, status: "fulfilled" as const },
  { id: "#1035", date: "2026-03-18", customer: "Amy L.", city: "Boston, MA", items: "Super Smash Bros (N64)", total: 39.99, status: "fulfilled" as const },
];

const ORDER_TABS = [
  { id: "all", label: "All", count: 8 },
  { id: "unfulfilled", label: "Unfulfilled", count: 2 },
  { id: "fulfilled", label: "Fulfilled", count: 6 },
];

export default function OrdersPage() {
  const [activeTab, setActiveTab] = useState("all");

  const filtered = SAMPLE_ORDERS.filter((o) => {
    if (activeTab === "all") return true;
    return o.status === activeTab;
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Orders" description="Manage orders and fulfillment.">
        <Button variant="secondary" size="sm">
          <RefreshCw size={14} />
          Sync Orders
        </Button>
      </PageHeader>

      <Tabs tabs={ORDER_TABS} activeTab={activeTab} onChange={setActiveTab} />

      <Card>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-border">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Order</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Items</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Total</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Status</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">Actions</th>
                </tr>
              </thead>
              <motion.tbody variants={staggerContainer} initial="hidden" animate="visible">
                {filtered.map((order) => (
                  <motion.tr
                    key={order.id}
                    variants={staggerItem}
                    className="border-b border-border transition-colors hover:bg-bg-hover/50"
                  >
                    <td className="px-4 py-3 font-mono text-sm font-semibold text-accent-cyan">{order.id}</td>
                    <td className="px-4 py-3 text-sm text-text-secondary">{formatDate(order.date)}</td>
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-text-primary">{order.customer}</p>
                      <p className="text-xs text-text-muted">{order.city}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-text-secondary max-w-[200px] truncate">{order.items}</td>
                    <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-text-primary">{formatCurrency(order.total)}</td>
                    <td className="px-4 py-3 text-center">
                      <Badge variant={order.status === "unfulfilled" ? "warning" : "success"}>{order.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Button variant="ghost" size="icon">
                        <ExternalLink size={16} />
                      </Button>
                    </td>
                  </motion.tr>
                ))}
              </motion.tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
