"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { formatCurrency, formatRelativeTime } from "@/lib/utils";
import {
  Loader2,
  Search,
  AlertTriangle,
  Package,
  Truck,
  Clock,
  CheckCircle2,
  X,
} from "lucide-react";
import { useState } from "react";
import {
  useFulfillmentTasks,
  useUpdateFulfillmentTask,
  useCompleteFulfillment,
  useFulfillmentAlerts,
  useAcknowledgeAlert,
} from "@/hooks/use-fulfillment";
import Link from "next/link";
import type { FulfillmentTask, FulfillmentStatus } from "@/types/fulfillment";
import {
  FULFILLMENT_STATUS_LABELS,
  FULFILLMENT_STATUS_VARIANTS,
} from "@/types/fulfillment";

// ── Update Dialog ──────────────────────────────────────────────────

function UpdateTaskDialog({
  task,
  open,
  onClose,
}: {
  task: FulfillmentTask;
  open: boolean;
  onClose: () => void;
}) {
  const updateTask = useUpdateFulfillmentTask();
  const completeFulfillment = useCompleteFulfillment();

  const [ebayOrderId, setEbayOrderId] = useState(task.ebayOrderId ?? "");
  const [ebayPrice, setEbayPrice] = useState(
    task.ebayPurchasePrice?.toString() ?? ""
  );
  const [ebaySellerName, setEbaySeller] = useState(task.ebaySellerName ?? "");
  const [trackingNumber, setTracking] = useState(task.trackingNumber ?? "");
  const [trackingCarrier, setCarrier] = useState(task.trackingCarrier ?? "USPS");
  const [notes, setNotes] = useState(task.notes ?? "");

  const handleMarkOrdered = () => {
    updateTask.mutate(
      {
        id: task.id,
        status: "ordered_on_ebay",
        ebayOrderId: ebayOrderId || undefined,
        ebayPurchasePrice: ebayPrice ? parseFloat(ebayPrice) : undefined,
        ebaySellerName: ebaySellerName || undefined,
        notes: notes || undefined,
      },
      { onSuccess: onClose }
    );
  };

  const handleAddTracking = () => {
    updateTask.mutate(
      {
        id: task.id,
        status: "shipped",
        trackingNumber: trackingNumber || undefined,
        trackingCarrier: trackingCarrier || undefined,
        notes: notes || undefined,
      },
      { onSuccess: onClose }
    );
  };

  const handleMarkDelivered = () => {
    updateTask.mutate(
      { id: task.id, status: "delivered" },
      { onSuccess: onClose }
    );
  };

  const handleMarkFulfilled = () => {
    completeFulfillment.mutate(task.id, { onSuccess: onClose });
  };

  const handleCancel = () => {
    updateTask.mutate(
      { id: task.id, status: "cancelled" },
      { onSuccess: onClose }
    );
  };

  const handleSaveNotes = () => {
    updateTask.mutate(
      {
        id: task.id,
        ebayOrderId: ebayOrderId || undefined,
        ebayPurchasePrice: ebayPrice ? parseFloat(ebayPrice) : undefined,
        ebaySellerName: ebaySellerName || undefined,
        notes: notes || undefined,
      },
      { onSuccess: onClose }
    );
  };

  const isPending = updateTask.isPending || completeFulfillment.isPending;

  return (
    <Dialog open={open} onClose={onClose} title={`Update: ${task.lineItemTitle}`}>
      <div className="space-y-4">
        {/* Current status */}
        <div className="flex items-center justify-between rounded-[var(--radius-md)] bg-bg-nested p-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Status
          </span>
          <Badge variant={FULFILLMENT_STATUS_VARIANTS[task.status]}>
            {FULFILLMENT_STATUS_LABELS[task.status]}
          </Badge>
        </div>

        {/* eBay Order Info (show for pending/ordered) */}
        {(task.status === "pending" || task.status === "ordered_on_ebay") && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-text-primary">
              eBay Purchase Details
            </h4>
            <Input
              placeholder="eBay Order ID"
              value={ebayOrderId}
              onChange={(e) => setEbayOrderId(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                placeholder="Purchase price"
                type="number"
                step="0.01"
                value={ebayPrice}
                onChange={(e) => setEbayPrice(e.target.value)}
              />
              <Input
                placeholder="Seller name"
                value={ebaySellerName}
                onChange={(e) => setEbaySeller(e.target.value)}
              />
            </div>
          </div>
        )}

        {/* Tracking Info (show for ordered/awaiting/shipped) */}
        {(task.status === "ordered_on_ebay" ||
          task.status === "awaiting_shipment" ||
          task.status === "shipped") && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-text-primary">
              Tracking Info
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <Input
                placeholder="Tracking number"
                value={trackingNumber}
                onChange={(e) => setTracking(e.target.value)}
              />
              <select
                className="rounded-[var(--radius-md)] border border-border bg-bg-surface px-3 py-2 text-sm text-text-primary"
                value={trackingCarrier}
                onChange={(e) => setCarrier(e.target.value)}
              >
                <option value="USPS">USPS</option>
                <option value="UPS">UPS</option>
                <option value="FedEx">FedEx</option>
                <option value="DHL">DHL</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>
        )}

        {/* Notes */}
        <div>
          <textarea
            className="w-full rounded-[var(--radius-md)] border border-border bg-bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-cyan focus:outline-none"
            placeholder="Notes..."
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          {task.status === "pending" && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleMarkOrdered}
              disabled={isPending}
            >
              {isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Package size={14} />
              )}
              Mark Ordered on eBay
            </Button>
          )}

          {(task.status === "ordered_on_ebay" ||
            task.status === "awaiting_shipment") &&
            trackingNumber && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleAddTracking}
                disabled={isPending}
              >
                {isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Truck size={14} />
                )}
                Add Tracking & Mark Shipped
              </Button>
            )}

          {task.status === "shipped" && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleMarkDelivered}
              disabled={isPending}
            >
              <CheckCircle2 size={14} />
              Mark Delivered
            </Button>
          )}

          {(task.status === "delivered" || task.status === "shipped") && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleMarkFulfilled}
              disabled={isPending}
            >
              <CheckCircle2 size={14} />
              Fulfill on Shopify
            </Button>
          )}

          {/* Save notes/details without status change */}
          {task.status !== "fulfilled" && task.status !== "cancelled" && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSaveNotes}
              disabled={isPending}
            >
              Save Details
            </Button>
          )}

          {task.status !== "fulfilled" && task.status !== "cancelled" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCancel}
              disabled={isPending}
            >
              <X size={14} />
              Cancel
            </Button>
          )}
        </div>
      </div>
    </Dialog>
  );
}

// ── Main Page ──────────────────────────────────────────────────────

export default function FulfillmentPage() {
  const [activeTab, setActiveTab] = useState("all");
  const [editingTask, setEditingTask] = useState<FulfillmentTask | null>(null);

  const { data, isLoading } = useFulfillmentTasks();
  const { data: alertsData } = useFulfillmentAlerts();
  const acknowledgeAlert = useAcknowledgeAlert();

  const tasks: FulfillmentTask[] = data?.tasks ?? [];
  const alerts = alertsData?.alerts ?? [];

  // Counts for tabs
  const pendingCount = tasks.filter((t) => t.status === "pending").length;
  const orderedCount = tasks.filter(
    (t) => t.status === "ordered_on_ebay" || t.status === "awaiting_shipment"
  ).length;
  const inTransitCount = tasks.filter((t) => t.status === "shipped").length;
  const deliveredCount = tasks.filter((t) => t.status === "delivered").length;
  const fulfilledCount = tasks.filter((t) => t.status === "fulfilled").length;

  const TABS = [
    { id: "all", label: "All", count: tasks.length },
    { id: "pending", label: "Pending", count: pendingCount },
    { id: "ordered", label: "Ordered", count: orderedCount },
    { id: "in_transit", label: "In Transit", count: inTransitCount },
    { id: "delivered", label: "Delivered", count: deliveredCount },
    { id: "fulfilled", label: "Fulfilled", count: fulfilledCount },
  ];

  const filtered = tasks.filter((t) => {
    if (activeTab === "all") return true;
    if (activeTab === "pending") return t.status === "pending";
    if (activeTab === "ordered")
      return t.status === "ordered_on_ebay" || t.status === "awaiting_shipment";
    if (activeTab === "in_transit") return t.status === "shipped";
    if (activeTab === "delivered") return t.status === "delivered";
    if (activeTab === "fulfilled") return t.status === "fulfilled";
    return true;
  });

  // KPI calculations
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 86400000);
  const completedThisWeek = tasks.filter(
    (t) => t.status === "fulfilled" && t.fulfilledAt && new Date(t.fulfilledAt) >= weekAgo
  ).length;

  const totalProfit = tasks
    .filter((t) => t.status === "fulfilled" && t.profit != null)
    .reduce((sum, t) => sum + (t.profit ?? 0), 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Fulfillment"
        description="Track eBay purchases for Shopify orders."
      >
        <Link href="/orders">
          <Button variant="secondary" size="sm">
            View Orders
          </Button>
        </Link>
      </PageHeader>

      {/* Alerts Banner */}
      {alerts.length > 0 && (
        <Card>
          <CardContent>
            <div className="space-y-2">
              {alerts.slice(0, 5).map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between rounded-[var(--radius-md)] bg-orange-50 border border-orange-200 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={16} className="text-orange-500" />
                    <span className="text-sm text-text-primary">
                      {alert.message}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => acknowledgeAlert.mutate(alert.id)}
                  >
                    Dismiss
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-orange-100 p-2">
                <Clock size={20} className="text-orange-500" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Pending
                </p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">
                  {pendingCount}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-blue-100 p-2">
                <Package size={20} className="text-blue-500" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Awaiting Shipment
                </p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">
                  {orderedCount}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-cyan-100 p-2">
                <Truck size={20} className="text-cyan-600" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  In Transit
                </p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">
                  {inTransitCount}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-[var(--radius-md)] bg-green-100 p-2">
                <CheckCircle2 size={20} className="text-green-600" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Completed (7d)
                </p>
                <p className="text-2xl font-bold tabular-nums text-text-primary">
                  {completedThisWeek}
                </p>
                {totalProfit > 0 && (
                  <p className="text-xs text-green-600 font-medium">
                    {formatCurrency(totalProfit)} profit
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      {/* Task Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-accent-cyan" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <Truck size={48} className="mx-auto mb-3 text-text-muted opacity-40" />
              <p className="text-sm text-text-muted">
                {activeTab === "all"
                  ? "No fulfillment tasks yet. Create them from the Order Detail page."
                  : "No tasks in this category."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-border">
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Order
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Item
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Customer
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                      eBay Order
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Cost
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Profit
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Age
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Actions
                    </th>
                  </tr>
                </thead>
                <motion.tbody
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                  key={activeTab}
                >
                  {filtered.map((task) => (
                    <motion.tr
                      key={task.id}
                      variants={staggerItem}
                      className="border-b border-border transition-colors hover:bg-bg-hover/50"
                    >
                      <td className="px-4 py-3">
                        <Link
                          href={`/orders/${encodeURIComponent(task.shopifyOrderId)}`}
                          className="font-mono text-sm font-semibold text-accent-cyan hover:underline"
                        >
                          {task.shopifyOrderNumber}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-text-primary max-w-[200px] truncate">
                          {task.lineItemTitle}
                        </p>
                        {task.lineItemSku && (
                          <p className="text-xs text-text-muted">{task.lineItemSku}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-sm text-text-primary">{task.customerName}</p>
                        <p className="text-xs text-text-muted">{task.customerCity}</p>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant={FULFILLMENT_STATUS_VARIANTS[task.status as FulfillmentStatus]}>
                          {FULFILLMENT_STATUS_LABELS[task.status as FulfillmentStatus]}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        {task.ebayOrderId ? (
                          <span className="font-mono text-xs text-text-secondary">
                            {task.ebayOrderId}
                          </span>
                        ) : (
                          <span className="text-xs text-text-muted">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums">
                        {task.ebayPurchasePrice != null
                          ? formatCurrency(task.ebayPurchasePrice)
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums">
                        {task.profit != null ? (
                          <span
                            className={
                              task.profit >= 0 ? "text-green-600" : "text-red-500"
                            }
                          >
                            {formatCurrency(task.profit)}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-4 py-3 text-center text-xs text-text-muted">
                        {formatRelativeTime(task.createdAt)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Link
                            href={`/ebay?q=${encodeURIComponent(task.lineItemTitle)}`}
                          >
                            <Button variant="ghost" size="icon" title="Search eBay">
                              <Search size={16} />
                            </Button>
                          </Link>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Update"
                            onClick={() => setEditingTask(task)}
                          >
                            <Package size={16} />
                          </Button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </motion.tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Update Dialog */}
      {editingTask && (
        <UpdateTaskDialog
          task={editingTask}
          open={!!editingTask}
          onClose={() => setEditingTask(null)}
        />
      )}
    </div>
  );
}
