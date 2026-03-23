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
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );
`);

export { schema };
