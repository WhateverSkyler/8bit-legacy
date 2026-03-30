"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatDate } from "@/lib/utils";
import { Search, Truck, Loader2, ArrowLeft, Plus } from "lucide-react";
import { useParams } from "next/navigation";
import { useOrders } from "@/hooks/use-orders";
import { useFulfillmentTasks, useCreateFulfillmentTask } from "@/hooks/use-fulfillment";
import Link from "next/link";
import type { Order } from "@/types/order";
import { FULFILLMENT_STATUS_LABELS, FULFILLMENT_STATUS_VARIANTS } from "@/types/fulfillment";

export default function OrderDetailPage() {
  const params = useParams();
  const orderId = decodeURIComponent(params.id as string);
  const { data, isLoading } = useOrders();
  const { data: fulfillmentData } = useFulfillmentTasks();
  const createTask = useCreateFulfillmentTask();
  const fulfillmentTasks = fulfillmentData?.tasks ?? [];

  const order: Order | undefined = data?.orders?.find(
    (o: Order) => o.id === orderId || o.orderNumber === orderId
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={32} className="animate-spin text-accent-cyan" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="space-y-6">
        <PageHeader title="Order Not Found" description="This order could not be loaded." />
        <Link href="/orders">
          <Button variant="secondary" size="sm">
            <ArrowLeft size={14} />
            Back to Orders
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title={`Order ${order.orderNumber}`} description={`Placed ${formatDate(order.createdAt)}`}>
        <div className="flex items-center gap-2">
          <Link href="/orders">
            <Button variant="secondary" size="sm">
              <ArrowLeft size={14} />
              Back
            </Button>
          </Link>
          {order.status === "unfulfilled" && (
            <Button variant="primary" size="sm">
              <Truck size={14} />
              Mark Fulfilled
            </Button>
          )}
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-4">Line Items</h3>
              <div className="space-y-3">
                {order.lineItems.map((item, i) => {
                  const existingTask = fulfillmentTasks.find(
                    (t) =>
                      t.shopifyOrderId === order.id &&
                      t.lineItemTitle === item.title
                  );

                  return (
                    <div key={i} className="rounded-[var(--radius-md)] bg-bg-nested p-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-text-primary">{item.title}</p>
                          <p className="text-xs text-text-secondary">
                            {item.sku ? `${item.sku} \u00B7 ` : ""}Qty: {item.quantity}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold tabular-nums text-text-primary">
                            {formatCurrency(item.price * item.quantity)}
                          </span>
                          <Link href={`/ebay?q=${encodeURIComponent(item.title)}`}>
                            <Button variant="outline" size="sm">
                              <Search size={14} />
                              Find on eBay
                            </Button>
                          </Link>
                        </div>
                      </div>
                      {/* Fulfillment Status */}
                      <div className="mt-2 flex items-center justify-between border-t border-border/50 pt-2">
                        {existingTask ? (
                          <div className="flex items-center gap-2">
                            <Badge variant={FULFILLMENT_STATUS_VARIANTS[existingTask.status as keyof typeof FULFILLMENT_STATUS_VARIANTS]}>
                              {FULFILLMENT_STATUS_LABELS[existingTask.status as keyof typeof FULFILLMENT_STATUS_LABELS]}
                            </Badge>
                            {existingTask.ebayOrderId && (
                              <span className="font-mono text-xs text-text-muted">
                                eBay: {existingTask.ebayOrderId}
                              </span>
                            )}
                            <Link href="/fulfillment">
                              <Button variant="ghost" size="sm">
                                Manage
                              </Button>
                            </Link>
                          </div>
                        ) : (
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={createTask.isPending}
                            onClick={() =>
                              createTask.mutate({
                                shopifyOrderId: order.id,
                                shopifyOrderNumber: order.orderNumber,
                                lineItemTitle: item.title,
                                lineItemSku: item.sku,
                                lineItemPrice: item.price,
                                lineItemQuantity: item.quantity,
                                lineItemImageUrl: item.imageUrl,
                                customerName: order.customerName,
                                customerCity: order.customerCity,
                              })
                            }
                          >
                            {createTask.isPending ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <Plus size={14} />
                            )}
                            Create Fulfillment Task
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Order Total */}
          <Card>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold uppercase tracking-wide text-text-muted">Total</span>
                <span className="text-lg font-bold tabular-nums text-text-primary">{formatCurrency(order.totalPrice)}</span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Customer</h3>
              <p className="text-sm font-medium text-text-primary">{order.customerName}</p>
              <p className="text-xs text-text-secondary mt-1">{order.customerCity}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Status</h3>
              <Badge variant={order.status === "unfulfilled" ? "warning" : "success"}>{order.status}</Badge>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
