"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, Truck } from "lucide-react";

export default function OrderDetailPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Order #1042" description="Order details and fulfillment.">
        <Button variant="primary" size="sm">
          <Truck size={14} />
          Mark Fulfilled
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Line Items</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-[var(--radius-md)] bg-bg-nested p-3">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Super Mario Bros 3</p>
                    <p className="text-xs text-text-secondary">NES &middot; Qty: 1</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold tabular-nums text-text-primary">$34.99</span>
                    <Button variant="outline" size="sm">
                      <Search size={14} />
                      Find on eBay
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Customer</h3>
              <p className="text-sm font-medium text-text-primary">Alex M.</p>
              <p className="text-xs text-text-secondary mt-1">Atlanta, GA 30301</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Status</h3>
              <Badge variant="warning">Unfulfilled</Badge>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
