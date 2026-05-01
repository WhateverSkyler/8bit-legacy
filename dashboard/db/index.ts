import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { join } from "path";
import * as schema from "./schema";

const DB_PATH = join(process.cwd(), "db", "8bitlegacy.db");

const sqlite = new Database(DB_PATH);

// Enable WAL mode for better concurrent read performance
sqlite.pragma("journal_mode = WAL");

export const db = drizzle(sqlite, { schema });

// Initialize tables on first import
sqlite.exec(`
  CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    handle TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    image_url TEXT,
    created_at TEXT,
    updated_at TEXT,
    synced_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS variants (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id),
    title TEXT NOT NULL,
    sku TEXT NOT NULL DEFAULT '',
    price REAL NOT NULL,
    barcode TEXT NOT NULL DEFAULT '',
    synced_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    order_number TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_city TEXT NOT NULL DEFAULT '',
    total_price REAL NOT NULL,
    synced_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS order_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(id),
    title TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    sku TEXT NOT NULL DEFAULT '',
    image_url TEXT
  );

  CREATE TABLE IF NOT EXISTS price_sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    total_items INTEGER NOT NULL,
    changes_applied INTEGER NOT NULL,
    below_profit INTEGER NOT NULL,
    unmatched INTEGER NOT NULL,
    net_adjustment REAL NOT NULL
  );

  CREATE TABLE IF NOT EXISTS price_sync_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES price_sync_runs(id),
    product_title TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    market_price REAL NOT NULL,
    old_price REAL NOT NULL,
    new_price REAL NOT NULL,
    price_diff REAL NOT NULL,
    estimated_profit REAL NOT NULL,
    status TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS ebay_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    max_price REAL,
    results_json TEXT NOT NULL,
    searched_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS social_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    caption TEXT NOT NULL,
    product TEXT NOT NULL,
    product_url TEXT NOT NULL DEFAULT '',
    image_url TEXT NOT NULL DEFAULT '',
    image_suggestion TEXT NOT NULL DEFAULT '',
    platform TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    scheduled_at TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL,
    buffer_id TEXT,
    buffer_profile_id TEXT,
    engagement_likes INTEGER DEFAULT 0,
    engagement_comments INTEGER DEFAULT 0,
    engagement_shares INTEGER DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );

  -- Automation system
  CREATE TABLE IF NOT EXISTS automation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    items_processed INTEGER DEFAULT 0,
    items_changed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata_json TEXT
  );

  -- Fulfillment tracker
  CREATE TABLE IF NOT EXISTS fulfillment_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shopify_order_id TEXT NOT NULL,
    shopify_order_number TEXT NOT NULL,
    line_item_title TEXT NOT NULL,
    line_item_sku TEXT NOT NULL DEFAULT '',
    line_item_price REAL NOT NULL,
    line_item_quantity INTEGER NOT NULL DEFAULT 1,
    line_item_image_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    ebay_order_id TEXT,
    ebay_listing_url TEXT,
    ebay_purchase_price REAL,
    ebay_seller_name TEXT,
    tracking_number TEXT,
    tracking_carrier TEXT,
    customer_name TEXT NOT NULL,
    customer_city TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    ordered_at TEXT,
    shipped_at TEXT,
    delivered_at TEXT,
    fulfilled_at TEXT,
    notes TEXT
  );

  CREATE TABLE IF NOT EXISTS fulfillment_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
  );

  -- Pricing automation
  CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_title TEXT NOT NULL,
    console_name TEXT NOT NULL,
    loose_price REAL NOT NULL,
    cib_price REAL DEFAULT 0,
    new_price REAL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'scraper',
    scraped_at TEXT NOT NULL
  );

  -- Google Ads
  CREATE TABLE IF NOT EXISTS google_ads_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    conversion_value REAL NOT NULL DEFAULT 0,
    roas REAL DEFAULT 0,
    cpc REAL DEFAULT 0,
    synced_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS google_ads_search_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    search_term TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    is_negative INTEGER NOT NULL DEFAULT 0,
    synced_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS google_ads_conversion_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shopify_order_id TEXT NOT NULL UNIQUE,
    shopify_order_number TEXT,
    conversion_type TEXT NOT NULL,
    gclid TEXT,
    hashed_email TEXT,
    hashed_phone TEXT,
    conversion_value REAL NOT NULL,
    currency_code TEXT NOT NULL,
    conversion_date_time TEXT NOT NULL,
    upload_status TEXT NOT NULL DEFAULT 'pending',
    google_ads_response TEXT,
    error_message TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    uploaded_at TEXT
  );

  CREATE TABLE IF NOT EXISTS google_ads_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    action_type TEXT NOT NULL,
    target_entity_type TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    target_entity_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 1,
    error_message TEXT
  );
`);

// Add new columns for price staleness tracking (safe to run multiple times)
try {
  sqlite.exec(`ALTER TABLE variants ADD COLUMN last_price_check TEXT`);
} catch {
  // Column already exists
}
try {
  sqlite.exec(`ALTER TABLE variants ADD COLUMN last_market_price REAL`);
} catch {
  // Column already exists
}

export { schema };
