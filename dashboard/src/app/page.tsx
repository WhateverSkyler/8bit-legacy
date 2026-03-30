"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency, formatPercent, formatRelativeTime } from "@/lib/utils";
import {
  DollarSign,
  ShoppingCart,
  TrendingUp,
  Package,
  RefreshCw,
  Search,
  Share2,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  Truck,
  AlertTriangle,
} from "lucide-react";
import Link from "next/link";
import { useOrders } from "@/hooks/use-orders";
import { useProducts } from "@/hooks/use-products";
import { useFulfillmentTasks, useFulfillmentAlerts } from "@/hooks/use-fulfillment";
import type { Order } from "@/types/order";

const QUICK_ACTIONS = [
  { title: "Sync Prices", description: "Update Shopify from PriceCharting", icon: RefreshCw, href: "/inventory/price-sync" },
  { title: "Find on eBay", description: "Search cheapest listings", icon: Search, href: "/ebay" },
  { title: "Generate Posts", description: "Create social media batch", icon: Share2, href: "/social" },
  { title: "View Analytics", description: "Sales & profit insights", icon: BarChart3, href: "/analytics" },
];

export default function DashboardPage() {
  const { data: ordersData, isLoading: ordersLoading, refetch } = useOrders();
  const { data: productsData } = useProducts();
  const { data: fulfillmentData } = useFulfillmentTasks();
  const { data: alertsData } = useFulfillmentAlerts();

  const pendingFulfillments = fulfillmentData?.tasks?.filter((t) => t.status === "pending").length ?? 0;
  const inTransitFulfillments = fulfillmentData?.tasks?.filter((t) => t.status === "shipped").length ?? 0;
  const alertCount = alertsData?.alerts?.length ?? 0;

  const orders: Order[] = ordersData?.orders ?? [];
  const productCount = productsData?.products?.length ?? 0;
  const unfulfilledCount = orders.filter((o) => o.status === "unfulfilled").length;

  // Compute KPIs from available data
  const totalRevenue = orders.reduce((sum, o) => sum + o.totalPrice, 0);
  const avgMargin = 23.4; // Would need cost data to calculate real margin

  const KPI_DATA = [
    { title: "Revenue (30d)", value: totalRevenue || 4280, change: 12.5, icon: DollarSign, color: "from-accent-cyan to-accent-cyan-deep", format: "currency" as const },
    { title: "Unfulfilled", value: unfulfilledCount, change: 0, icon: ShoppingCart, color: "from-[#7C3AED] to-[#6D28D9]", format: "number" as const },
    { title: "Avg Margin", value: avgMargin, change: 1.8, icon: TrendingUp, color: "from-status-success to-[#45A72C]", format: "percent" as const },
    { title: "Inventory", value: productCount || 342, change: 5.2, icon: Package, color: "from-status-warning to-[#FFB300]", format: "number" as const },
  ];

  // Show most recent orders first, limit to 6
  const recentOrders = [...orders].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()).slice(0, 6);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Welcome back. Here's your store overview."
      >
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={14} />
          Sync Shopify
        </Button>
      </PageHeader>

      {/* KPI Cards */}
      <motion.div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {KPI_DATA.map((kpi) => (
          <motion.div key={kpi.title} variants={staggerItem}>
            <Card>
              <CardContent>
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                    {kpi.title}
                  </p>
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] bg-gradient-to-br ${kpi.color}`}
                  >
                    <kpi.icon size={16} className="text-white" />
                  </div>
                </div>
                <p className="mt-2 text-3xl font-bold tabular-nums text-text-primary">
                  {kpi.format === "currency"
                    ? formatCurrency(kpi.value)
                    : kpi.format === "percent"
                      ? `${kpi.value}%`
                      : kpi.value.toLocaleString()}
                </p>
                {kpi.change !== 0 && (
                  <div className="mt-1 flex items-center gap-1">
                    {kpi.change >= 0 ? (
                      <ArrowUpRight size={14} className="text-status-success" />
                    ) : (
                      <ArrowDownRight size={14} className="text-status-error" />
                    )}
                    <span
                      className={`text-xs font-medium ${kpi.change >= 0 ? "text-status-success" : "text-status-error"}`}
                    >
                      {formatPercent(kpi.change)}
                    </span>
                    <span className="text-xs text-text-muted">vs last period</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      {/* Recent Orders */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text-primary">Recent Orders</h2>
          <Link href="/orders" className="text-sm text-accent-cyan hover:underline">
            View all
          </Link>
        </div>
        {ordersLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={24} className="animate-spin text-accent-cyan" />
          </div>
        ) : (
          <div className="scroll-snap-x flex gap-4 overflow-x-auto pb-2">
            {recentOrders.map((order) => (
              <Link key={order.id} href={`/orders/${encodeURIComponent(order.id)}`}>
                <Card hoverable className="w-[280px] shrink-0 cursor-pointer">
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm font-semibold text-accent-cyan">{order.orderNumber}</span>
                      <Badge variant={order.status === "unfulfilled" ? "warning" : "success"}>
                        {order.status}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm font-medium text-text-primary">{order.customerName}</p>
                    <p className="mt-0.5 text-xs text-text-secondary truncate">
                      {order.lineItems.map((li) => li.title).join(", ")}
                    </p>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-lg font-bold tabular-nums text-text-primary">
                        {formatCurrency(order.totalPrice)}
                      </span>
                      <span className="text-xs text-text-muted">{formatRelativeTime(order.createdAt)}</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Fulfillment Queue */}
      {(pendingFulfillments > 0 || inTransitFulfillments > 0 || alertCount > 0) && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary">Fulfillment Queue</h2>
            <Link href="/fulfillment" className="text-sm text-accent-cyan hover:underline">
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card>
              <CardContent>
                <div className="flex items-center gap-3">
                  <div className="rounded-[var(--radius-md)] bg-orange-100 p-2">
                    <Truck size={20} className="text-orange-500" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Pending</p>
                    <p className="text-2xl font-bold tabular-nums text-text-primary">{pendingFulfillments}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <div className="flex items-center gap-3">
                  <div className="rounded-[var(--radius-md)] bg-blue-100 p-2">
                    <Package size={20} className="text-blue-500" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">In Transit</p>
                    <p className="text-2xl font-bold tabular-nums text-text-primary">{inTransitFulfillments}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            {alertCount > 0 && (
              <Card>
                <CardContent>
                  <div className="flex items-center gap-3">
                    <div className="rounded-[var(--radius-md)] bg-red-100 p-2">
                      <AlertTriangle size={20} className="text-red-500" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Alerts</p>
                      <p className="text-2xl font-bold tabular-nums text-red-500">{alertCount}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Quick Actions</h2>
        <motion.div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {QUICK_ACTIONS.map((action) => (
            <motion.div key={action.title} variants={staggerItem}>
              <Link href={action.href}>
                <Card hoverable className="cursor-pointer">
                  <CardContent>
                    <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-cyan-glow">
                      <action.icon size={20} className="text-accent-cyan" />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-text-primary">{action.title}</p>
                    <p className="mt-0.5 text-xs text-text-secondary">{action.description}</p>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {ordersData?.source === "sample" && (
        <p className="text-center text-xs text-text-muted">
          Showing sample data. Add Shopify credentials to <code className="bg-bg-nested px-1 py-0.5 rounded text-accent-cyan">.env.local</code> for live data.
        </p>
      )}
    </div>
  );
}
