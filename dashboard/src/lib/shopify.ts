import "server-only";
import type { ShopifyProduct } from "./matching";
import type { Order } from "@/types/order";

/**
 * Shopify GraphQL client — ported from scripts/price-sync.py and scripts/ebay-finder.py
 */

interface ShopifyConfig {
  storeUrl: string;
  accessToken: string;
}

function getGraphQLUrl(config: ShopifyConfig): string {
  return `https://${config.storeUrl}/admin/api/2024-10/graphql.json`;
}

export async function shopifyGraphQL(
  config: ShopifyConfig,
  query: string,
  variables?: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const url = getGraphQLUrl(config);

  const payload: Record<string, unknown> = { query };
  if (variables) payload.variables = variables;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "X-Shopify-Access-Token": config.accessToken,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    throw new Error(`Shopify API error: ${resp.status} ${resp.statusText}`);
  }

  const data = await resp.json();

  if (data.errors) {
    console.error("Shopify GraphQL errors:", data.errors);
  }

  return data;
}

/**
 * Fetch all products from Shopify with their variants and prices.
 * Ported from Python's fetch_all_shopify_products()
 */
export async function fetchAllProducts(
  config: ShopifyConfig,
  onProgress?: (page: number, count: number) => void
): Promise<ShopifyProduct[]> {
  const products: ShopifyProduct[] = [];
  let cursor: string | null = null;
  let page = 0;

  while (true) {
    page++;
    const afterClause = cursor ? `, after: "${cursor}"` : "";
    const query = `
      {
        products(first: 50${afterClause}) {
          edges {
            cursor
            node {
              id
              title
              handle
              tags
              variants(first: 10) {
                edges {
                  node {
                    id
                    title
                    sku
                    price
                    barcode
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
          }
        }
      }
    `;

    const data = await shopifyGraphQL(config, query);
    const productsData = (data as any).data?.products;
    const edges = productsData?.edges ?? [];

    for (const edge of edges) {
      const node = edge.node;
      for (const variantEdge of node.variants.edges) {
        const variant = variantEdge.node;
        products.push({
          productId: node.id,
          productTitle: node.title,
          productHandle: node.handle,
          productTags: node.tags,
          variantId: variant.id,
          variantTitle: variant.title,
          sku: variant.sku ?? "",
          currentPrice: parseFloat(variant.price),
          barcode: variant.barcode ?? "",
        });
      }
    }

    onProgress?.(page, products.length);

    const hasNext = productsData?.pageInfo?.hasNextPage ?? false;
    if (!hasNext || edges.length === 0) break;

    cursor = edges[edges.length - 1].cursor;

    // Rate limiting
    await new Promise((r) => setTimeout(r, 500));
  }

  return products;
}

/**
 * Fetch unfulfilled orders from Shopify.
 * Ported from Python's fetch_pending_shopify_orders()
 */
export async function fetchUnfulfilledOrders(
  config: ShopifyConfig
): Promise<Order[]> {
  const query = `
    {
      orders(first: 25, query: "fulfillment_status:unfulfilled") {
        edges {
          node {
            id
            name
            createdAt
            displayFulfillmentStatus
            totalPriceSet {
              shopMoney {
                amount
              }
            }
            shippingAddress {
              name
              city
              provinceCode
              zip
            }
            lineItems(first: 20) {
              edges {
                node {
                  title
                  quantity
                  image {
                    url
                  }
                  variant {
                    price
                    sku
                  }
                }
              }
            }
          }
        }
      }
    }
  `;

  const data = await shopifyGraphQL(config, query);
  const edges = (data as any).data?.orders?.edges ?? [];

  return edges.map((edge: any) => {
    const node = edge.node;
    const shipping = node.shippingAddress ?? {};
    return {
      id: node.id,
      orderNumber: node.name,
      createdAt: node.createdAt,
      status: "unfulfilled" as const,
      customerName: shipping.name ?? "Unknown",
      customerCity: [shipping.city, shipping.provinceCode, shipping.zip]
        .filter(Boolean)
        .join(", "),
      totalPrice: parseFloat(
        node.totalPriceSet?.shopMoney?.amount ?? "0"
      ),
      lineItems: node.lineItems.edges.map((liEdge: any) => {
        const li = liEdge.node;
        return {
          title: li.title,
          quantity: li.quantity,
          price: parseFloat(li.variant?.price ?? "0"),
          sku: li.variant?.sku ?? "",
          imageUrl: li.image?.url ?? null,
        };
      }),
    };
  });
}

/**
 * Update a single variant's price on Shopify.
 */
export async function updateVariantPrice(
  config: ShopifyConfig,
  variantId: string,
  price: number
): Promise<{ success: boolean; errors?: string[] }> {
  const mutation = `
    mutation productVariantUpdate($input: ProductVariantInput!) {
      productVariantUpdate(input: $input) {
        productVariant {
          id
          price
        }
        userErrors {
          field
          message
        }
      }
    }
  `;

  const data = await shopifyGraphQL(config, mutation, {
    input: {
      id: variantId,
      price: price.toString(),
    },
  });

  const result = (data as any).data?.productVariantUpdate;
  const userErrors = result?.userErrors ?? [];

  if (userErrors.length > 0) {
    return {
      success: false,
      errors: userErrors.map((e: any) => `${e.field}: ${e.message}`),
    };
  }

  return { success: true };
}

/**
 * Mark an order as fulfilled with tracking info.
 */
export async function fulfillOrder(
  config: ShopifyConfig,
  orderId: string,
  trackingNumber: string,
  carrier: string
): Promise<{ success: boolean; errors?: string[] }> {
  // First get the fulfillment order ID
  const query = `
    {
      order(id: "${orderId}") {
        fulfillmentOrders(first: 1) {
          edges {
            node {
              id
              lineItems(first: 20) {
                edges {
                  node {
                    id
                    remainingQuantity
                  }
                }
              }
            }
          }
        }
      }
    }
  `;

  const orderData = await shopifyGraphQL(config, query);
  const fulfillmentOrder = (orderData as any).data?.order?.fulfillmentOrders
    ?.edges?.[0]?.node;

  if (!fulfillmentOrder) {
    return { success: false, errors: ["No fulfillment order found"] };
  }

  const lineItems = fulfillmentOrder.lineItems.edges.map((e: any) => ({
    id: e.node.id,
    quantity: e.node.remainingQuantity,
  }));

  const mutation = `
    mutation fulfillmentCreate($fulfillment: FulfillmentInput!) {
      fulfillmentCreate(fulfillment: $fulfillment) {
        fulfillment {
          id
          status
        }
        userErrors {
          field
          message
        }
      }
    }
  `;

  const data = await shopifyGraphQL(config, mutation, {
    fulfillment: {
      lineItemsByFulfillmentOrder: [
        {
          fulfillmentOrderId: fulfillmentOrder.id,
          fulfillmentOrderLineItems: lineItems,
        },
      ],
      trackingInfo: {
        number: trackingNumber,
        company: carrier,
      },
    },
  });

  const result = (data as any).data?.fulfillmentCreate;
  const userErrors = result?.userErrors ?? [];

  if (userErrors.length > 0) {
    return {
      success: false,
      errors: userErrors.map((e: any) => `${e.field}: ${e.message}`),
    };
  }

  return { success: true };
}
