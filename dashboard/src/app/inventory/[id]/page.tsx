"use client";

import { useParams } from "next/navigation";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import {
  ArrowLeft,
  Search,
  DollarSign,
  Package,
  Tag,
  Loader2,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

interface ProductData {
  productId: string;
  productTitle: string;
  productTags: string[];
  imageUrl?: string | null;
  variants: Array<{
    variantId: string;
    variantTitle: string;
    sku: string;
    currentPrice: number;
    barcode: string;
  }>;
}

export default function ProductDetailPage() {
  const params = useParams();
  const productGid = `gid://${params.id}`;

  const { data, isLoading } = useQuery<{ products: ProductData[] }>({
    queryKey: ["products"],
    queryFn: async () => {
      const res = await fetch("/api/shopify/products");
      if (!res.ok) throw new Error("Failed to fetch products");
      return res.json();
    },
  });

  const product = data?.products?.find((p) => p.productId === productGid);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={32} className="animate-spin text-accent-cyan" />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="space-y-4">
        <PageHeader title="Product Not Found" description="This product doesn't exist in the local cache.">
          <Link href="/inventory">
            <Button variant="secondary" size="sm">
              <ArrowLeft size={14} />
              Back to Inventory
            </Button>
          </Link>
        </PageHeader>
      </div>
    );
  }

  const console = product.productTags[0] ?? "";
  const isPokemon = product.productTags.some((t) => t.toLowerCase() === "pokemon");
  const multiplier = isPokemon ? 1.15 : 1.35;
  const primarySku = product.variants[0]?.sku ?? "";

  return (
    <div className="space-y-6">
      <PageHeader
        title={product.productTitle}
        description={`${console}${primarySku ? ` · SKU: ${primarySku}` : ""}`}
      >
        <div className="flex gap-2">
          <Link href="/inventory">
            <Button variant="secondary" size="sm">
              <ArrowLeft size={14} />
              Back
            </Button>
          </Link>
          <Link href={`/ebay?q=${encodeURIComponent(product.productTitle)}`}>
            <Button variant="secondary" size="sm">
              <Search size={14} />
              Find on eBay
            </Button>
          </Link>
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Variants & Pricing Table */}
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">
                Variants & Pricing
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                      <th className="pb-2">Variant</th>
                      <th className="pb-2">SKU</th>
                      <th className="pb-2 text-right">Price</th>
                      <th className="pb-2 text-right">Est. Market</th>
                      <th className="pb-2 text-right">Shopify Fee</th>
                      <th className="pb-2 text-right">Est. Profit</th>
                      <th className="pb-2 text-right">Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {product.variants.map((v) => {
                      const estimatedMarket = v.currentPrice / multiplier;
                      const shopifyFee = v.currentPrice * 0.029 + 0.30;
                      const estimatedProfit = v.currentPrice - estimatedMarket - shopifyFee;
                      const margin = v.currentPrice > 0 ? (estimatedProfit / v.currentPrice) * 100 : 0;

                      return (
                        <tr key={v.variantId} className="border-b border-border/50 last:border-0">
                          <td className="py-3 font-medium text-text-primary">
                            {v.variantTitle || "Default"}
                          </td>
                          <td className="py-3 font-mono text-xs text-text-muted">{v.sku || "—"}</td>
                          <td className="py-3 text-right font-bold tabular-nums text-text-primary">
                            {formatCurrency(v.currentPrice)}
                          </td>
                          <td className="py-3 text-right tabular-nums text-text-secondary">
                            {formatCurrency(estimatedMarket)}
                          </td>
                          <td className="py-3 text-right tabular-nums text-text-secondary">
                            {formatCurrency(shopifyFee)}
                          </td>
                          <td className={`py-3 text-right tabular-nums font-medium ${estimatedProfit >= 3 ? "text-status-success" : estimatedProfit >= 0 ? "text-status-warning" : "text-status-error"}`}>
                            {formatCurrency(estimatedProfit)}
                          </td>
                          <td className={`py-3 text-right tabular-nums ${margin >= 15 ? "text-status-success" : margin >= 5 ? "text-status-warning" : "text-status-error"}`}>
                            {margin.toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Tags */}
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {product.productTags.map((tag) => (
                  <Badge key={tag} variant="neutral">
                    <Tag size={10} className="mr-1" />
                    {tag}
                  </Badge>
                ))}
                {product.productTags.length === 0 && (
                  <span className="text-xs text-text-muted">No tags</span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Image */}
          <Card>
            <CardContent>
              <div className="flex aspect-square items-center justify-center rounded-[var(--radius-md)] bg-bg-nested mb-3">
                {product.imageUrl ? (
                  <img
                    src={product.imageUrl}
                    alt={product.productTitle}
                    className="h-full w-full rounded-[var(--radius-md)] object-contain"
                  />
                ) : (
                  <Package size={48} className="text-text-muted" />
                )}
              </div>
              {console && <Badge variant="info">{console}</Badge>}
              {isPokemon && <Badge variant="warning" className="ml-2">Pokemon</Badge>}
            </CardContent>
          </Card>

          {/* Profit Summary for primary variant */}
          {product.variants[0] && (() => {
            const v = product.variants[0];
            const market = v.currentPrice / multiplier;
            const fee = v.currentPrice * 0.029 + 0.30;
            const profit = v.currentPrice - market - fee;
            return (
              <Card>
                <CardContent>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">
                    Profit Calculator
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Sell Price</span>
                      <span className="font-semibold tabular-nums">{formatCurrency(v.currentPrice)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Est. Market Cost</span>
                      <span className="tabular-nums text-text-secondary">-{formatCurrency(market)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Shopify Fee</span>
                      <span className="tabular-nums text-text-secondary">-{formatCurrency(fee)}</span>
                    </div>
                    <div className="border-t border-border pt-2 flex justify-between">
                      <span className="font-medium text-text-primary">Net Profit</span>
                      <span className={`font-bold tabular-nums ${profit >= 3 ? "text-status-success" : profit >= 0 ? "text-status-warning" : "text-status-error"}`}>
                        {formatCurrency(profit)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })()}

          {/* Quick Actions */}
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Actions</h3>
              <div className="flex flex-col gap-2">
                <Link href={`/ebay?q=${encodeURIComponent(product.productTitle)}`}>
                  <Button variant="secondary" size="sm" className="w-full justify-start">
                    <Search size={14} />
                    Search eBay
                  </Button>
                </Link>
                <Link href="/inventory/price-sync">
                  <Button variant="secondary" size="sm" className="w-full justify-start">
                    <DollarSign size={14} />
                    Price Sync
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
