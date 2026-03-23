"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency } from "@/lib/utils";
import { Grid3X3, List, Upload, Search, Gamepad2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const SAMPLE_PRODUCTS = [
  { id: "1", title: "Super Mario Bros 3", console: "NES", price: 34.99, marketPrice: 25.92, margin: 22.6, status: "active" },
  { id: "2", title: "The Legend of Zelda: A Link to the Past", console: "SNES", price: 44.99, marketPrice: 33.33, margin: 21.4, status: "active" },
  { id: "3", title: "Sonic the Hedgehog 2", console: "Genesis", price: 14.99, marketPrice: 11.10, margin: 18.2, status: "active" },
  { id: "4", title: "GoldenEye 007", console: "N64", price: 29.99, marketPrice: 22.22, margin: 21.8, status: "active" },
  { id: "5", title: "Pokemon Red", console: "Game Boy", price: 49.99, marketPrice: 37.03, margin: 22.0, status: "active" },
  { id: "6", title: "Final Fantasy VII", console: "PS1", price: 39.99, marketPrice: 29.62, margin: 21.9, status: "active" },
  { id: "7", title: "Super Smash Bros", console: "N64", price: 39.99, marketPrice: 29.62, margin: 21.9, status: "active" },
  { id: "8", title: "Mega Man 2", console: "NES", price: 24.99, marketPrice: 18.51, margin: 20.6, status: "active" },
];

export default function InventoryPage() {
  const [view, setView] = useState<"grid" | "list">("grid");
  const [search, setSearch] = useState("");

  const filtered = SAMPLE_PRODUCTS.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Inventory" description="Manage products and pricing.">
        <Link href="/inventory/price-sync">
          <Button variant="primary" size="sm">
            <Upload size={14} />
            Price Sync
          </Button>
        </Link>
      </PageHeader>

      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <Input
            placeholder="Search products..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex rounded-[var(--radius-md)] border border-border bg-bg-nested p-0.5">
          <button
            onClick={() => setView("grid")}
            className={`rounded-[var(--radius-sm)] p-2 transition-colors ${view === "grid" ? "bg-bg-surface text-text-primary shadow-sm" : "text-text-muted hover:text-text-secondary"}`}
          >
            <Grid3X3 size={16} />
          </button>
          <button
            onClick={() => setView("list")}
            className={`rounded-[var(--radius-sm)] p-2 transition-colors ${view === "list" ? "bg-bg-surface text-text-primary shadow-sm" : "text-text-muted hover:text-text-secondary"}`}
          >
            <List size={16} />
          </button>
        </div>
      </div>

      {/* Product Grid */}
      {view === "grid" ? (
        <motion.div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {filtered.map((product) => (
            <motion.div key={product.id} variants={staggerItem}>
              <Link href={`/inventory/${product.id}`}>
                <Card hoverable className="cursor-pointer">
                  <CardContent>
                    <div className="flex h-32 items-center justify-center rounded-[var(--radius-md)] bg-bg-nested mb-3">
                      <Gamepad2 size={32} className="text-text-muted" />
                    </div>
                    <p className="text-sm font-semibold text-text-primary truncate">{product.title}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <Badge variant="info">{product.console}</Badge>
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-lg font-bold tabular-nums text-text-primary">{formatCurrency(product.price)}</span>
                      <span className="text-xs text-status-success font-medium">{product.margin}% margin</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <Card>
          <CardContent>
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-border">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Product</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Console</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Market</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Price</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Margin</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.id} className="border-b border-border hover:bg-bg-hover/50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-text-primary">{p.title}</td>
                    <td className="px-4 py-3"><Badge variant="info">{p.console}</Badge></td>
                    <td className="px-4 py-3 text-right text-sm tabular-nums text-text-secondary">{formatCurrency(p.marketPrice)}</td>
                    <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-text-primary">{formatCurrency(p.price)}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-status-success">{p.margin}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
