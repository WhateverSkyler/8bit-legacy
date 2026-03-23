"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { Search, ExternalLink, ShoppingCart } from "lucide-react";
import { useState } from "react";

const SAMPLE_RESULTS = [
  { title: "Super Mario Bros 3 NES Cartridge - Tested Working", price: 18.99, shipping: 3.99, total: 22.98, seller: "retro_games_usa", rating: "99.2%", condition: "Used" },
  { title: "Super Mario Bros. 3 (NES) Authentic Cart Only", price: 19.50, shipping: 4.25, total: 23.75, seller: "game_vault_88", rating: "98.7%", condition: "Used" },
  { title: "Super Mario Bros 3 Nintendo NES Game Cartridge", price: 20.00, shipping: 3.50, total: 23.50, seller: "pixel_paradise", rating: "99.5%", condition: "Used" },
  { title: "Mario Bros 3 NES - Cleaned & Tested", price: 21.99, shipping: 0.0, total: 21.99, seller: "classic_ctrl", rating: "97.8%", condition: "Used" },
  { title: "Super Mario Bros. 3 NES Authentic - Free Ship", price: 24.99, shipping: 0.0, total: 24.99, seller: "nostalgic_gamer", rating: "99.1%", condition: "Used" },
];

export default function EbayPage() {
  const [query, setQuery] = useState("Super Mario Bros 3 NES");
  const [searched, setSearched] = useState(true);
  const shopifyPrice = 34.99;

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
                onKeyDown={(e) => e.key === "Enter" && setSearched(true)}
              />
            </div>
            <Button variant="primary" onClick={() => setSearched(true)}>
              <Search size={14} />
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {searched && (
        <Card>
          <CardContent>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">
                  {SAMPLE_RESULTS.length} results for <span className="font-medium text-text-primary">&ldquo;{query}&rdquo;</span>
                </p>
                <p className="text-xs text-text-muted mt-0.5">
                  Shopify price: <span className="text-accent-cyan font-medium">{formatCurrency(shopifyPrice)}</span>
                </p>
              </div>
              <Button variant="secondary" size="sm">
                <ShoppingCart size={14} />
                Bulk Search Orders
              </Button>
            </div>
            <motion.div className="space-y-2" variants={staggerContainer} initial="hidden" animate="visible">
              {SAMPLE_RESULTS.map((listing, i) => {
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
                        <span className="text-status-success">{listing.rating}</span>
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
                      <Button variant="ghost" size="icon" aria-label="Open on eBay">
                        <ExternalLink size={16} />
                      </Button>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
