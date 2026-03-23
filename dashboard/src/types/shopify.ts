export interface ShopifyProductNode {
  id: string;
  title: string;
  handle: string;
  tags: string[];
  variants: {
    edges: {
      node: {
        id: string;
        title: string;
        sku: string;
        price: string;
        barcode: string;
      };
    }[];
  };
  images: {
    edges: {
      node: {
        url: string;
      };
    }[];
  };
}

export interface ShopifyOrderNode {
  id: string;
  name: string;
  createdAt: string;
  displayFulfillmentStatus: string;
  totalPriceSet: {
    shopMoney: {
      amount: string;
    };
  };
  shippingAddress: {
    name: string;
    city: string;
    provinceCode: string;
    zip: string;
  } | null;
  lineItems: {
    edges: {
      node: {
        title: string;
        quantity: number;
        image: { url: string } | null;
        variant: {
          price: string;
          sku: string;
        } | null;
      };
    }[];
  };
}

export interface ShopifyGraphQLResponse<T> {
  data: T;
  errors?: { message: string }[];
}
