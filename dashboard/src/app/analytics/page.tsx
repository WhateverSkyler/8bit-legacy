"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency, formatPercent } from "@/lib/utils";
import {
  DollarSign,
  ShoppingCart,
  TrendingUp,
  Target,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const REVENUE_DATA = Array.from({ length: 30 }, (_, i) => ({
  day: `${i + 1}`,
  revenue: Math.floor(80 + Math.random() * 200),
}));

const PROFIT_DATA = [
  { month: "Oct", revenue: 3200, cogs: 2100, fees: 140, profit: 960 },
  { month: "Nov", revenue: 4800, cogs: 3100, fees: 200, profit: 1500 },
  { month: "Dec", revenue: 6200, cogs: 4000, fees: 260, profit: 1940 },
  { month: "Jan", revenue: 3800, cogs: 2500, fees: 160, profit: 1140 },
  { month: "Feb", revenue: 4100, cogs: 2700, fees: 170, profit: 1230 },
  { month: "Mar", revenue: 4280, cogs: 2800, fees: 180, profit: 1300 },
];

const CONSOLE_DATA = [
  { name: "NES", value: 28, color: "#0EA5E9" },
  { name: "SNES", value: 22, color: "#8B5CF6" },
  { name: "N64", value: 18, color: "#22C55E" },
  { name: "Game Boy", value: 15, color: "#F59E0B" },
  { name: "PS1", value: 10, color: "#EF4444" },
  { name: "Other", value: 7, color: "#9CA3AF" },
];

const KPI = [
  { title: "Total Revenue", value: 4280, change: 12.5, icon: DollarSign, prefix: "$" },
  { title: "Total Orders", value: 87, change: 8.3, icon: ShoppingCart },
  { title: "Avg Order Value", value: 49.2, change: 3.7, icon: TrendingUp, prefix: "$" },
  { title: "Google Ads ROAS", value: 520, change: -4.2, icon: Target, suffix: "%" },
];

export default function AnalyticsPage() {
  return (
    <div className="space-y-8">
      <PageHeader title="Analytics" description="Sales, profit, and advertising insights." />

      {/* KPIs */}
      <motion.div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {KPI.map((kpi) => (
          <motion.div key={kpi.title} variants={staggerItem}>
            <Card>
              <CardContent>
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">{kpi.title}</p>
                  <kpi.icon size={16} className="text-text-muted" />
                </div>
                <p className="mt-2 text-2xl font-bold tabular-nums text-text-primary">
                  {kpi.prefix}{kpi.value.toLocaleString()}{kpi.suffix}
                </p>
                <div className="mt-1 flex items-center gap-1">
                  {kpi.change >= 0 ? <ArrowUpRight size={14} className="text-status-success" /> : <ArrowDownRight size={14} className="text-status-error" />}
                  <span className={`text-xs font-medium ${kpi.change >= 0 ? "text-status-success" : "text-status-error"}`}>{formatPercent(kpi.change)}</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      {/* Revenue Chart */}
      <Card>
        <CardContent>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Revenue (Last 30 Days)</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={REVENUE_DATA}>
                <defs>
                  <linearGradient id="cyanGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="day" tick={{ fill: "#9CA3AF", fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: "#9CA3AF", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  contentStyle={{ background: "#fff", border: "1px solid #E2E5E9", borderRadius: 8, color: "#111827", fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
                  formatter={(value) => [formatCurrency(Number(value)), "Revenue"]}
                />
                <Area type="monotone" dataKey="revenue" stroke="#0EA5E9" strokeWidth={2} fill="url(#cyanGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Profit Breakdown */}
        <Card>
          <CardContent>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Profit Breakdown (6 Mo)</h3>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={PROFIT_DATA}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis dataKey="month" tick={{ fill: "#9CA3AF", fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: "#9CA3AF", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E2E5E9", borderRadius: 8, color: "#111827", fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }} />
                  <Bar dataKey="profit" fill="#22C55E" radius={[4, 4, 0, 0]} name="Profit" />
                  <Bar dataKey="cogs" fill="#0EA5E9" radius={[4, 4, 0, 0]} name="COGS" />
                  <Bar dataKey="fees" fill="#EF4444" radius={[4, 4, 0, 0]} name="Fees" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Console Breakdown */}
        <Card>
          <CardContent>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Sales by Console</h3>
            <div className="h-[280px] flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={CONSOLE_DATA}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {CONSOLE_DATA.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E2E5E9", borderRadius: 8, color: "#111827", fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-3 mt-2">
              {CONSOLE_DATA.map((c) => (
                <div key={c.name} className="flex items-center gap-1.5 text-xs text-text-secondary">
                  <span className="h-2 w-2 rounded-full" style={{ background: c.color }} />
                  {c.name} ({c.value}%)
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
