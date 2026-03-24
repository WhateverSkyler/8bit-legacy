"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { Search, ExternalLink, Loader2 } from "lucide-react";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useEbaySearch } from "@/hooks/use-ebay-search";

export default function EbayPage() {
  return (
    <Suspense>
      <EbayPageInner />
    </Suspense>
  );
}

function EbayPageInner() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const shopifyPrice = 34.99;

  // Update when navigated to with ?q= param
  useEffect(() => {
    const q = searchParams.get("q");
    if (q && q !== query) {
      setQuery(q);
      setSearchQuery(q);
    }
  }, [searchParams]);

  const { data, isLoading } = useEbaySearch(searchQuery, {
    enabled: searchQuery.length > 0,
  });

  const handleSearch = () => {
    if (query.trim()) setSearchQuery(query.trim());
  };

  const results = data?.results ?? [];
  const isFallback = data?.isFallback ?? false;

  return (
    <div className="space-y-6">
      <PageHeader title="eBay Finder" description="Find cheapest listings for fulfillment." />

      {/* Search */}
      <Card>
        <CardContent>
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <Input
                placeholder="Search eBay..."
                className="pl-9"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
            </div>
            <Button variant="primary" onClick={handleSearch} disabled={isLoading}>
              {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {searchQuery && !isLoading && (
        <Card>
          <CardContent>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">
                  {results.length} results for <span className="font-medium text-text-primary">&ldquo;{searchQuery}&rdquo;</span>
                  {isFallback && results.length === 0 && (
                    <span className="ml-2 text-text-muted">(eBay API not configured)</span>
                  )}
                </p>
                <p className="text-xs text-text-muted mt-0.5">
                  Shopify price: <span className="text-accent-cyan font-medium">{formatCurrency(shopifyPrice)}</span>
                </p>
              </div>
              {isFallback && data?.fallbackUrl && (
                <a href={data.fallbackUrl} target="_blank" rel="noopener noreferrer">
                  <Button variant="secondary" size="sm">
                    <ExternalLink size={14} />
                    Search on eBay.com
                  </Button>
                </a>
              )}
            </div>

            {results.length > 0 ? (
              <motion.div className="space-y-2" variants={staggerContainer} initial="hidden" animate="visible" key={searchQuery}>
                {results.map((listing, i) => {
                  const profit = shopifyPrice - listing.total - (shopifyPrice * 0.029 + 0.30);
                  return (
                    <motion.div
                      key={i}
                      variants={staggerItem}
                      className="flex items-center justify-between rounded-[var(--radius-md)] border border-border bg-bg-nested p-4 transition-colors hover:border-accent-cyan/30 hover:bg-bg-hover/50"
                    >
                      <div className="flex-1 min-w-0 mr-4">
                        <p className="text-sm font-medium text-text-primary truncate">{listing.title}</p>
                        <div className="mt-1 flex items-center gap-3 text-xs text-text-secondary">
                          <span>{listing.seller}</span>
                          <span className="text-status-success">{listing.sellerFeedback}</span>
                          <Badge variant="neutral">{listing.condition}</Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-6 shrink-0">
                        <div className="text-right">
                          <p className="text-sm font-bold tabular-nums text-text-primary">{formatCurrency(listing.total)}</p>
                          <p className="text-xs text-text-muted tabular-nums">
                            {formatCurrency(listing.price)} + {formatCurrency(listing.shipping)} ship
                          </p>
                        </div>
                        <div className="text-right w-20">
                          <p className={`text-sm font-semibold tabular-nums ${profit >= 0 ? "text-status-success" : "text-status-error"}`}>
                            {formatCurrency(profit)}
                          </p>
                          <p className="text-xs text-text-muted">profit</p>
                        </div>
                        {listing.url && (
                          <a href={listing.url} target="_blank" rel="noopener noreferrer">
                            <Button variant="ghost" size="icon" aria-label="Open on eBay">
                              <ExternalLink size={16} />
                            </Button>
                          </a>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            ) : isFallback ? (
              <p className="text-center text-sm text-text-muted py-8">
                eBay API not configured. Use the button above to search directly on eBay.com.
              </p>
            ) : (
              <p className="text-center text-sm text-text-muted py-8">
                No results found.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <Card>
          <CardContent>
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-accent-cyan" />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
