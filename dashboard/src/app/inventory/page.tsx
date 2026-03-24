"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency } from "@/lib/utils";
import { Grid3X3, List, Upload, Search, Gamepad2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState, useMemo } from "react";
import { useProducts } from "@/hooks/use-products";

interface ShopifyProduct {
  productId: string;
  productTitle: string;
  productHandle: string;
  productTags: string[];
  variantId: string;
  variantTitle: string;
  sku: string;
  currentPrice: number;
  barcode: string;
}

export default function InventoryPage() {
  const [view, setView] = useState<"grid" | "list">("grid");
  const [search, setSearch] = useState("");
  const { data, isLoading } = useProducts();

  const products: ShopifyProduct[] = data?.products ?? [];

  const filtered = useMemo(() => {
    if (!search) return products;
    const q = search.toLowerCase();
    return products.filter(
      (p) =>
        p.productTitle.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.productTags.some((t: string) => t.toLowerCase().includes(q))
    );
  }, [products, search]);

  // Estimate margin using 1.35x multiplier assumption (market price = current / 1.35)
  const getEstimatedMargin = (price: number) => {
    const estimatedMarket = price / 1.35;
    const fees = price * 0.029 + 0.30;
    const profit = price - estimatedMarket - fees;
    return Math.round((profit / price) * 1000) / 10;
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Inventory" description={`${products.length} products in store.`}>
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

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={24} className="animate-spin text-accent-cyan" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-sm text-text-muted">
          {search ? "No products match your search." : "No products found."}
        </div>
      ) : view === "grid" ? (
        <motion.div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          key={`grid-${search}`}
        >
          {filtered.map((product) => {
            const console = product.productTags[0] ?? "";
            const margin = getEstimatedMargin(product.currentPrice);
            return (
              <motion.div key={product.variantId} variants={staggerItem}>
                <Link href={`/inventory/${product.productId.replace("gid://", "")}`}>
                  <Card hoverable className="cursor-pointer">
                    <CardContent>
                      <div className="flex h-32 items-center justify-center rounded-[var(--radius-md)] bg-bg-nested mb-3">
                        <Gamepad2 size={32} className="text-text-muted" />
                      </div>
                      <p className="text-sm font-semibold text-text-primary truncate">{product.productTitle}</p>
                      <div className="mt-1 flex items-center gap-2">
                        {console && <Badge variant="info">{console}</Badge>}
                        {product.sku && <span className="text-xs text-text-muted font-mono">{product.sku}</span>}
                      </div>
                      <div className="mt-3 flex items-center justify-between">
                        <span className="text-lg font-bold tabular-nums text-text-primary">{formatCurrency(product.currentPrice)}</span>
                        <span className={`text-xs font-medium ${margin >= 15 ? "text-status-success" : margin >= 5 ? "text-status-warning" : "text-status-error"}`}>
                          ~{margin}% margin
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            );
          })}
        </motion.div>
      ) : (
        <Card>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-border">
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Product</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Console</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">SKU</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Price</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Margin</th>
                  </tr>
                </thead>
                <motion.tbody variants={staggerContainer} initial="hidden" animate="visible" key={`list-${search}`}>
                  {filtered.map((p) => {
                    const margin = getEstimatedMargin(p.currentPrice);
                    return (
                      <motion.tr key={p.variantId} variants={staggerItem} className="border-b border-border hover:bg-bg-hover/50 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-text-primary">{p.productTitle}</td>
                        <td className="px-4 py-3">{p.productTags[0] && <Badge variant="info">{p.productTags[0]}</Badge>}</td>
                        <td className="px-4 py-3 text-sm text-text-muted font-mono">{p.sku}</td>
                        <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-text-primary">{formatCurrency(p.currentPrice)}</td>
                        <td className={`px-4 py-3 text-right text-sm font-medium ${margin >= 15 ? "text-status-success" : margin >= 5 ? "text-status-warning" : "text-status-error"}`}>
                          ~{margin}%
                        </td>
                      </motion.tr>
                    );
                  })}
                </motion.tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {data?.source === "sample" && (
        <p className="text-center text-xs text-text-muted">
          Showing sample data. Add Shopify credentials to <code className="bg-bg-nested px-1 py-0.5 rounded text-accent-cyan">.env.local</code> for live inventory.
        </p>
      )}
    </div>
  );
}
