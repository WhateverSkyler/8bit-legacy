"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency } from "@/lib/utils";
import { Save, Gamepad2 } from "lucide-react";

export default function ProductDetailPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Super Mario Bros 3" description="NES &middot; SKU: SMB3-NES-001">
        <Button variant="primary" size="sm">
          <Save size={14} />
          Save Changes
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Product Details</h3>
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-text-secondary mb-1 block">Title</label>
                  <Input defaultValue="Super Mario Bros 3" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-text-secondary mb-1 block">Price</label>
                    <Input type="number" defaultValue="34.99" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-secondary mb-1 block">Market Price</label>
                    <Input type="number" defaultValue="25.92" disabled />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardContent>
              <div className="flex h-48 items-center justify-center rounded-[var(--radius-md)] bg-bg-nested mb-3">
                <Gamepad2 size={48} className="text-text-muted" />
              </div>
              <Badge variant="info">NES</Badge>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Profit Calculator</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-text-secondary">Sell Price</span><span className="font-semibold tabular-nums">{formatCurrency(34.99)}</span></div>
                <div className="flex justify-between"><span className="text-text-secondary">Market Cost</span><span className="tabular-nums text-text-secondary">-{formatCurrency(25.92)}</span></div>
                <div className="flex justify-between"><span className="text-text-secondary">Shopify Fee</span><span className="tabular-nums text-text-secondary">-{formatCurrency(1.31)}</span></div>
                <div className="border-t border-border pt-2 flex justify-between"><span className="font-medium text-text-primary">Net Profit</span><span className="font-bold text-status-success tabular-nums">{formatCurrency(7.76)}</span></div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
