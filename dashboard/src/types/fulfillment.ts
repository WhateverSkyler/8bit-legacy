export type FulfillmentStatus =
  | "pending"
  | "ordered_on_ebay"
  | "awaiting_shipment"
  | "shipped"
  | "delivered"
  | "fulfilled"
  | "cancelled";

export interface FulfillmentTask {
  id: number;
  shopifyOrderId: string;
  shopifyOrderNumber: string;
  lineItemTitle: string;
  lineItemSku: string;
  lineItemPrice: number;
  lineItemQuantity: number;
  lineItemImageUrl: string | null;
  status: FulfillmentStatus;
  ebayOrderId: string | null;
  ebayListingUrl: string | null;
  ebayPurchasePrice: number | null;
  ebaySellerName: string | null;
  trackingNumber: string | null;
  trackingCarrier: string | null;
  customerName: string;
  customerCity: string;
  createdAt: string;
  orderedAt: string | null;
  shippedAt: string | null;
  deliveredAt: string | null;
  fulfilledAt: string | null;
  notes: string | null;
  profit?: number; // computed: lineItemPrice - ebayPurchasePrice - fees
}

export interface FulfillmentAlert {
  id: number;
  taskId: number | null;
  type: "pending_too_long" | "no_tracking" | "delivery_exception" | "cost_overrun";
  message: string;
  severity: "info" | "warning" | "critical";
  acknowledged: boolean;
  createdAt: string;
}

export const FULFILLMENT_STATUS_LABELS: Record<FulfillmentStatus, string> = {
  pending: "Pending",
  ordered_on_ebay: "Ordered",
  awaiting_shipment: "Awaiting Shipment",
  shipped: "Shipped",
  delivered: "Delivered",
  fulfilled: "Fulfilled",
  cancelled: "Cancelled",
};

export const FULFILLMENT_STATUS_VARIANTS: Record<FulfillmentStatus, "warning" | "info" | "neutral" | "success" | "error"> = {
  pending: "warning",
  ordered_on_ebay: "info",
  awaiting_shipment: "neutral",
  shipped: "info",
  delivered: "success",
  fulfilled: "success",
  cancelled: "error",
};
