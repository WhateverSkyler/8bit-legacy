"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency, formatPercent } from "@/lib/utils";
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
} from "lucide-react";
import Link from "next/link";

const KPI_DATA = [
  {
    title: "Revenue (30d)",
    value: 4280.0,
    change: 12.5,
    icon: DollarSign,
    color: "from-accent-cyan to-accent-cyan-deep",
  },
  {
    title: "Orders Today",
    value: 7,
    change: -2.1,
    icon: ShoppingCart,
    color: "from-[#7C3AED] to-[#6D28D9]",
  },
  {
    title: "Avg Margin",
    value: 23.4,
    change: 1.8,
    icon: TrendingUp,
    color: "from-status-success to-[#45A72C]",
    suffix: "%",
  },
  {
    title: "Inventory",
    value: 342,
    change: 5.2,
    icon: Package,
    color: "from-status-warning to-[#FFB300]",
  },
];

const QUICK_ACTIONS = [
  { title: "Sync Prices", description: "Update Shopify from PriceCharting", icon: RefreshCw, href: "/inventory/price-sync" },
  { title: "Find on eBay", description: "Search cheapest listings", icon: Search, href: "/ebay" },
  { title: "Generate Posts", description: "Create social media batch", icon: Share2, href: "/social" },
  { title: "View Analytics", description: "Sales & profit insights", icon: BarChart3, href: "/analytics" },
];

const RECENT_ORDERS = [
  { id: "#1042", customer: "Alex M.", items: "Super Mario Bros 3 (NES)", total: 34.99, status: "unfulfilled" as const, time: "2h ago" },
  { id: "#1041", customer: "Sarah K.", items: "Pokemon Red (GB)", total: 49.99, status: "unfulfilled" as const, time: "5h ago" },
  { id: "#1040", customer: "Mike R.", items: "GoldenEye 007 (N64)", total: 29.99, status: "fulfilled" as const, time: "1d ago" },
  { id: "#1039", customer: "Lisa P.", items: "Sonic 2 (Genesis)", total: 14.99, status: "fulfilled" as const, time: "1d ago" },
  { id: "#1038", customer: "James T.", items: "Final Fantasy VII (PS1)", total: 39.99, status: "fulfilled" as const, time: "2d ago" },
  { id: "#1037", customer: "Emma D.", items: "Mega Man 2 (NES)", total: 24.99, status: "fulfilled" as const, time: "3d ago" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Welcome back. Here's your store overview."
      >
        <Button variant="secondary" size="sm">
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
                  {kpi.suffix
                    ? `${kpi.value}${kpi.suffix}`
                    : kpi.title.includes("Revenue")
                      ? formatCurrency(kpi.value)
                      : kpi.value.toLocaleString()}
                </p>
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
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      {/* Recent Orders — Horizontal Scroll (Switch tile style) */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text-primary">Recent Orders</h2>
          <Link href="/orders" className="text-sm text-accent-cyan hover:underline">
            View all
          </Link>
        </div>
        <div className="scroll-snap-x flex gap-4 overflow-x-auto pb-2">
          {RECENT_ORDERS.map((order) => (
            <Card key={order.id} hoverable className="w-[280px] shrink-0 cursor-pointer">
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold text-accent-cyan">{order.id}</span>
                  <Badge variant={order.status === "unfulfilled" ? "warning" : "success"}>
                    {order.status}
                  </Badge>
                </div>
                <p className="mt-2 text-sm font-medium text-text-primary">{order.customer}</p>
                <p className="mt-0.5 text-xs text-text-secondary truncate">{order.items}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-lg font-bold tabular-nums text-text-primary">
                    {formatCurrency(order.total)}
                  </span>
                  <span className="text-xs text-text-muted">{order.time}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

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
    </div>
  );
}
