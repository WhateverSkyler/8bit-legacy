import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

// Cached Shopify products
export const products = sqliteTable("products", {
  shopifyId: text("id").primaryKey(), // Shopify product GID
  title: text("title").notNull(),
  handle: text("handle").notNull(),
  tags: text("tags").notNull().default("[]"), // comma-separated string
  imageUrl: text("image_url"),
  createdAt: text("created_at"),
  updatedAt: text("updated_at"),
  syncedAt: text("synced_at").notNull(),
});

// Cached Shopify variants
export const variants = sqliteTable("variants", {
  shopifyVariantId: text("id").primaryKey(), // Shopify variant GID
  productShopifyId: text("product_id")
    .notNull()
    .references(() => products.shopifyId),
  title: text("title").notNull(),
  sku: text("sku").notNull().default(""),
  price: real("price").notNull(),
  barcode: text("barcode").notNull().default(""),
  syncedAt: text("synced_at").notNull(),
  lastPriceCheck: text("last_price_check"), // ISO timestamp of last price validation
  lastMarketPrice: real("last_market_price"), // most recent market price from PriceCharting
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
  bufferId: text("buffer_id"),
  bufferProfileId: text("buffer_profile_id"),
  engagementLikes: integer("engagement_likes").default(0),
  engagementComments: integer("engagement_comments").default(0),
  engagementShares: integer("engagement_shares").default(0),
});

// Key-value settings store
export const settings = sqliteTable("settings", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
  updatedAt: text("updated_at").notNull(),
});

// ── Automation System Tables ───────────────────────────────────────

// Generic automation run log (all scheduled jobs)
export const automationRuns = sqliteTable("automation_runs", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  jobName: text("job_name").notNull(),
  startedAt: text("started_at").notNull(),
  finishedAt: text("finished_at"),
  status: text("status").notNull().default("running"), // running, success, failed, cancelled
  itemsProcessed: integer("items_processed").default(0),
  itemsChanged: integer("items_changed").default(0),
  errorMessage: text("error_message"),
  metadataJson: text("metadata_json"), // flexible JSON for job-specific data
});

// ── Fulfillment Tracker Tables ─────────────────────────────────────

// Links Shopify order line items to eBay purchases
export const fulfillmentTasks = sqliteTable("fulfillment_tasks", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  shopifyOrderId: text("shopify_order_id").notNull(),
  shopifyOrderNumber: text("shopify_order_number").notNull(),
  lineItemTitle: text("line_item_title").notNull(),
  lineItemSku: text("line_item_sku").notNull().default(""),
  lineItemPrice: real("line_item_price").notNull(),
  lineItemQuantity: integer("line_item_quantity").notNull().default(1),
  lineItemImageUrl: text("line_item_image_url"),
  status: text("status").notNull().default("pending"),
  // pending, ordered_on_ebay, awaiting_shipment, shipped, delivered, fulfilled, cancelled
  ebayOrderId: text("ebay_order_id"),
  ebayListingUrl: text("ebay_listing_url"),
  ebayPurchasePrice: real("ebay_purchase_price"),
  ebaySellerName: text("ebay_seller_name"),
  trackingNumber: text("tracking_number"),
  trackingCarrier: text("tracking_carrier"),
  customerName: text("customer_name").notNull(),
  customerCity: text("customer_city").notNull().default(""),
  createdAt: text("created_at").notNull(),
  orderedAt: text("ordered_at"),
  shippedAt: text("shipped_at"),
  deliveredAt: text("delivered_at"),
  fulfilledAt: text("fulfilled_at"),
  notes: text("notes"),
});

// Alerts for fulfillment issues
export const fulfillmentAlerts = sqliteTable("fulfillment_alerts", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  taskId: integer("task_id"),
  type: text("type").notNull(), // pending_too_long, no_tracking, delivery_exception, cost_overrun, thin_margin
  message: text("message").notNull(),
  severity: text("severity").notNull().default("warning"), // info, warning, critical
  acknowledged: integer("acknowledged").notNull().default(0),
  createdAt: text("created_at").notNull(),
});

// ── Pricing Automation Tables ──────────────────────────────────────

// Scraped PriceCharting price snapshots
export const priceSnapshots = sqliteTable("price_snapshots", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  productTitle: text("product_title").notNull(),
  consoleName: text("console_name").notNull(),
  loosePrice: real("loose_price").notNull(),
  cibPrice: real("cib_price").default(0),
  newPrice: real("new_price").default(0),
  source: text("source").notNull().default("scraper"), // scraper, csv_upload
  scrapedAt: text("scraped_at").notNull(),
});

// ── Google Ads Tables ──────────────────────────────────────────────

// Daily campaign/product performance data
export const googleAdsPerformance = sqliteTable("google_ads_performance", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  date: text("date").notNull(),
  entityType: text("entity_type").notNull(), // campaign, ad_group, product
  entityId: text("entity_id").notNull(),
  entityName: text("entity_name").notNull(),
  impressions: integer("impressions").notNull().default(0),
  clicks: integer("clicks").notNull().default(0),
  cost: real("cost").notNull().default(0),
  conversions: integer("conversions").notNull().default(0),
  conversionValue: real("conversion_value").notNull().default(0),
  roas: real("roas").default(0),
  cpc: real("cpc").default(0),
  syncedAt: text("synced_at").notNull(),
});

// Search term report data
export const googleAdsSearchTerms = sqliteTable("google_ads_search_terms", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  date: text("date").notNull(),
  searchTerm: text("search_term").notNull(),
  campaignId: text("campaign_id").notNull(),
  impressions: integer("impressions").notNull().default(0),
  clicks: integer("clicks").notNull().default(0),
  cost: real("cost").notNull().default(0),
  conversions: integer("conversions").notNull().default(0),
  isNegative: integer("is_negative").notNull().default(0),
  syncedAt: text("synced_at").notNull(),
});

// Audit trail for automated ad actions
export const googleAdsActions = sqliteTable("google_ads_actions", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  runId: integer("run_id"),
  actionType: text("action_type").notNull(),
  // bid_increase, bid_decrease, pause_product, unpause_product, add_negative_keyword, budget_adjust
  targetEntityType: text("target_entity_type").notNull(),
  targetEntityId: text("target_entity_id").notNull(),
  targetEntityName: text("target_entity_name").notNull(),
  oldValue: text("old_value"),
  newValue: text("new_value"),
  reason: text("reason").notNull(),
  executedAt: text("executed_at").notNull(),
  success: integer("success").notNull().default(1),
  errorMessage: text("error_message"),
});
