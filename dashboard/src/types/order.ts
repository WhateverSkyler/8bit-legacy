export interface Order {
  id: string;
  orderNumber: string;
  createdAt: string;
  status: "unfulfilled" | "fulfilled" | "partially_fulfilled" | "cancelled";
  customerName: string;
  customerCity: string;
  totalPrice: number;
  lineItems: OrderLineItem[];
}

export interface OrderLineItem {
  title: string;
  quantity: number;
  price: number;
  sku: string;
  imageUrl: string | null;
}

export interface FulfillmentInfo {
  orderId: string;
  ebayOrderNumber?: string;
  trackingNumber?: string;
  carrier?: string;
  purchasedAt?: string;
  fulfilledAt?: string;
}
