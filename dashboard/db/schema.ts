import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

// Cached Shopify products
export const products = sqliteTable("products", {
  id: text("id").primaryKey(), // Shopify product GID
  title: text("title").notNull(),
  handle: text("handle").notNull(),
  tags: text("tags").notNull().default("[]"), // JSON array
  imageUrl: text("image_url"),
  createdAt: text("created_at"),
  updatedAt: text("updated_at"),
  syncedAt: text("synced_at").notNull(),
});

// Cached Shopify variants
export const variants = sqliteTable("variants", {
  id: text("id").primaryKey(), // Shopify variant GID
  productId: text("product_id")
    .notNull()
    .references(() => products.id),
  title: text("title").notNull(),
  sku: text("sku").notNull().default(""),
  price: real("price").notNull(),
  barcode: text("barcode").notNull().default(""),
  syncedAt: text("synced_at").notNull(),
});

// Cached Shopify orders
export const orders = sqliteTable("orders", {
  id: text("id").primaryKey(), // Shopify order GID
  orderNumber: text("order_number").notNull(),
  createdAt: text("created_at").notNull(),
  status: text("status").notNull(), // unfulfilled, fulfilled, etc.
  customerName: text("customer_name").notNull(),
  customerCity: text("customer_city").notNull().default(""),
  totalPrice: real("total_price").notNull(),
  syncedAt: text("synced_at").notNull(),
});

// Order line items
export const orderLineItems = sqliteTable("order_line_items", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  orderId: text("order_id")
    .notNull()
    .references(() => orders.id),
  title: text("title").notNull(),
  quantity: integer("quantity").notNull(),
  price: real("price").notNull(),
  sku: text("sku").notNull().default(""),
  imageUrl: text("image_url"),
});

// Price sync run history
export const priceSyncRuns = sqliteTable("price_sync_runs", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  timestamp: text("timestamp").notNull(),
  totalItems: integer("total_items").notNull(),
  changesApplied: integer("changes_applied").notNull(),
  belowProfit: integer("below_profit").notNull(),
  unmatched: integer("unmatched").notNull(),
  netAdjustment: real("net_adjustment").notNull(),
});

// Individual price changes per sync run
export const priceSyncItems = sqliteTable("price_sync_items", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  runId: integer("run_id")
    .notNull()
    .references(() => priceSyncRuns.id),
  productTitle: text("product_title").notNull(),
  variantId: text("variant_id").notNull(),
  marketPrice: real("market_price").notNull(),
  oldPrice: real("old_price").notNull(),
  newPrice: real("new_price").notNull(),
  priceDiff: real("price_diff").notNull(),
  estimatedProfit: real("estimated_profit").notNull(),
  status: text("status").notNull(), // applied, skipped, failed
});

// Saved eBay searches
export const ebaySearches = sqliteTable("ebay_searches", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  query: text("query").notNull(),
  maxPrice: real("max_price"),
  resultsJson: text("results_json").notNull(), // JSON array
  searchedAt: text("searched_at").notNull(),
});

// Generated social media posts
export const socialPosts = sqliteTable("social_posts", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  type: text("type").notNull(),
  caption: text("caption").notNull(),
  product: text("product").notNull(),
  productUrl: text("product_url").notNull().default(""),
  imageUrl: text("image_url").notNull().default(""),
  imageSuggestion: text("image_suggestion").notNull().default(""),
  platform: text("platform"),
  status: text("status").notNull().default("draft"), // draft, scheduled, published
  scheduledAt: text("scheduled_at"),
  publishedAt: text("published_at"),
  createdAt: text("created_at").notNull(),
});

// Key-value settings store
export const settings = sqliteTable("settings", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
  updatedAt: text("updated_at").notNull(),
});
