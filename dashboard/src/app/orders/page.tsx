"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency, formatDate } from "@/lib/utils";
import { RefreshCw, ExternalLink, Loader2 } from "lucide-react";
import { useState } from "react";
import { useOrders } from "@/hooks/use-orders";
import Link from "next/link";
import type { Order } from "@/types/order";

export default function OrdersPage() {
  const [activeTab, setActiveTab] = useState("all");
  const { data, isLoading, refetch, isRefetching } = useOrders({ status: activeTab as "all" | "unfulfilled" | "fulfilled" });

  const orders: Order[] = data?.orders ?? [];

  const allCount = orders.length;
  const unfulfilledCount = orders.filter((o) => o.status === "unfulfilled").length;
  const fulfilledCount = orders.filter((o) => o.status === "fulfilled").length;

  const ORDER_TABS = [
    { id: "all", label: "All", count: allCount },
    { id: "unfulfilled", label: "Unfulfilled", count: unfulfilledCount },
    { id: "fulfilled", label: "Fulfilled", count: fulfilledCount },
  ];

  const filtered = activeTab === "all" ? orders : orders.filter((o) => o.status === activeTab);

  return (
    <div className="space-y-6">
      <PageHeader title="Orders" description="Manage orders and fulfillment.">
        <Button variant="secondary" size="sm" onClick={() => refetch()} disabled={isRefetching}>
          {isRefetching ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Sync Orders
        </Button>
      </PageHeader>

      <Tabs tabs={ORDER_TABS} activeTab={activeTab} onChange={setActiveTab} />

      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-accent-cyan" />
            </div>
          ) : (
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
                <motion.tbody variants={staggerContainer} initial="hidden" animate="visible" key={activeTab}>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-sm text-text-muted">No orders found.</td>
                    </tr>
                  ) : (
                    filtered.map((order) => {
                      const itemSummary = order.lineItems.map((li) => `${li.title}${li.quantity > 1 ? ` x${li.quantity}` : ""}`).join(", ");
                      return (
                        <motion.tr
                          key={order.id}
                          variants={staggerItem}
                          className="border-b border-border transition-colors hover:bg-bg-hover/50"
                        >
                          <td className="px-4 py-3">
                            <Link href={`/orders/${encodeURIComponent(order.id)}`} className="font-mono text-sm font-semibold text-accent-cyan hover:underline">
                              {order.orderNumber}
                            </Link>
                          </td>
                          <td className="px-4 py-3 text-sm text-text-secondary">{formatDate(order.createdAt)}</td>
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium text-text-primary">{order.customerName}</p>
                            <p className="text-xs text-text-muted">{order.customerCity}</p>
                          </td>
                          <td className="px-4 py-3 text-sm text-text-secondary max-w-[200px] truncate">{itemSummary}</td>
                          <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-text-primary">{formatCurrency(order.totalPrice)}</td>
                          <td className="px-4 py-3 text-center">
                            <Badge variant={order.status === "unfulfilled" ? "warning" : "success"}>{order.status}</Badge>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Link href={`/orders/${encodeURIComponent(order.id)}`}>
                              <Button variant="ghost" size="icon">
                                <ExternalLink size={16} />
                              </Button>
                            </Link>
                          </td>
                        </motion.tr>
                      );
                    })
                  )}
                </motion.tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {data?.source === "sample" && (
        <p className="text-center text-xs text-text-muted">
          Showing sample data. Add Shopify credentials to <code className="bg-bg-nested px-1 py-0.5 rounded text-accent-cyan">.env.local</code> for live orders.
        </p>
      )}
    </div>
  );
}
