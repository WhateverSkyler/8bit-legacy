CREATE TABLE `automation_runs` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`job_name` text NOT NULL,
	`started_at` text NOT NULL,
	`finished_at` text,
	`status` text DEFAULT 'running' NOT NULL,
	`items_processed` integer DEFAULT 0,
	`items_changed` integer DEFAULT 0,
	`error_message` text,
	`metadata_json` text
);
--> statement-breakpoint
CREATE TABLE `ebay_searches` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`query` text NOT NULL,
	`max_price` real,
	`results_json` text NOT NULL,
	`searched_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `fulfillment_alerts` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`task_id` integer,
	`type` text NOT NULL,
	`message` text NOT NULL,
	`severity` text DEFAULT 'warning' NOT NULL,
	`acknowledged` integer DEFAULT 0 NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `fulfillment_tasks` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`shopify_order_id` text NOT NULL,
	`shopify_order_number` text NOT NULL,
	`line_item_title` text NOT NULL,
	`line_item_sku` text DEFAULT '' NOT NULL,
	`line_item_price` real NOT NULL,
	`line_item_quantity` integer DEFAULT 1 NOT NULL,
	`line_item_image_url` text,
	`status` text DEFAULT 'pending' NOT NULL,
	`ebay_order_id` text,
	`ebay_listing_url` text,
	`ebay_purchase_price` real,
	`ebay_seller_name` text,
	`tracking_number` text,
	`tracking_carrier` text,
	`customer_name` text NOT NULL,
	`customer_city` text DEFAULT '' NOT NULL,
	`created_at` text NOT NULL,
	`ordered_at` text,
	`shipped_at` text,
	`delivered_at` text,
	`fulfilled_at` text,
	`notes` text
);
--> statement-breakpoint
CREATE TABLE `google_ads_actions` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`run_id` integer,
	`action_type` text NOT NULL,
	`target_entity_type` text NOT NULL,
	`target_entity_id` text NOT NULL,
	`target_entity_name` text NOT NULL,
	`old_value` text,
	`new_value` text,
	`reason` text NOT NULL,
	`executed_at` text NOT NULL,
	`success` integer DEFAULT 1 NOT NULL,
	`error_message` text
);
--> statement-breakpoint
CREATE TABLE `google_ads_performance` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`date` text NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`entity_name` text NOT NULL,
	`impressions` integer DEFAULT 0 NOT NULL,
	`clicks` integer DEFAULT 0 NOT NULL,
	`cost` real DEFAULT 0 NOT NULL,
	`conversions` integer DEFAULT 0 NOT NULL,
	`conversion_value` real DEFAULT 0 NOT NULL,
	`roas` real DEFAULT 0,
	`cpc` real DEFAULT 0,
	`synced_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `google_ads_search_terms` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`date` text NOT NULL,
	`search_term` text NOT NULL,
	`campaign_id` text NOT NULL,
	`impressions` integer DEFAULT 0 NOT NULL,
	`clicks` integer DEFAULT 0 NOT NULL,
	`cost` real DEFAULT 0 NOT NULL,
	`conversions` integer DEFAULT 0 NOT NULL,
	`is_negative` integer DEFAULT 0 NOT NULL,
	`synced_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `order_line_items` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`order_id` text NOT NULL,
	`title` text NOT NULL,
	`quantity` integer NOT NULL,
	`price` real NOT NULL,
	`sku` text DEFAULT '' NOT NULL,
	`image_url` text,
	FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `orders` (
	`id` text PRIMARY KEY NOT NULL,
	`order_number` text NOT NULL,
	`created_at` text NOT NULL,
	`status` text NOT NULL,
	`customer_name` text NOT NULL,
	`customer_city` text DEFAULT '' NOT NULL,
	`total_price` real NOT NULL,
	`synced_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `price_snapshots` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`product_title` text NOT NULL,
	`console_name` text NOT NULL,
	`loose_price` real NOT NULL,
	`cib_price` real DEFAULT 0,
	`new_price` real DEFAULT 0,
	`source` text DEFAULT 'scraper' NOT NULL,
	`scraped_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `price_sync_items` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`run_id` integer NOT NULL,
	`product_title` text NOT NULL,
	`variant_id` text NOT NULL,
	`market_price` real NOT NULL,
	`old_price` real NOT NULL,
	`new_price` real NOT NULL,
	`price_diff` real NOT NULL,
	`estimated_profit` real NOT NULL,
	`status` text NOT NULL,
	FOREIGN KEY (`run_id`) REFERENCES `price_sync_runs`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `price_sync_runs` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`timestamp` text NOT NULL,
	`total_items` integer NOT NULL,
	`changes_applied` integer NOT NULL,
	`below_profit` integer NOT NULL,
	`unmatched` integer NOT NULL,
	`net_adjustment` real NOT NULL
);
--> statement-breakpoint
CREATE TABLE `products` (
	`shopify_id` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`handle` text NOT NULL,
	`vendor` text DEFAULT '' NOT NULL,
	`product_type` text DEFAULT '' NOT NULL,
	`tags` text DEFAULT '[]' NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`image_url` text,
	`created_at` text,
	`updated_at` text,
	`synced_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `settings` (
	`key` text PRIMARY KEY NOT NULL,
	`value` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `social_posts` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`type` text NOT NULL,
	`caption` text NOT NULL,
	`product` text NOT NULL,
	`product_url` text DEFAULT '' NOT NULL,
	`image_url` text DEFAULT '' NOT NULL,
	`image_suggestion` text DEFAULT '' NOT NULL,
	`platform` text,
	`status` text DEFAULT 'draft' NOT NULL,
	`scheduled_at` text,
	`published_at` text,
	`created_at` text NOT NULL,
	`buffer_id` text,
	`buffer_profile_id` text,
	`engagement_likes` integer DEFAULT 0,
	`engagement_comments` integer DEFAULT 0,
	`engagement_shares` integer DEFAULT 0
);
--> statement-breakpoint
CREATE TABLE `variants` (
	`shopify_variant_id` text PRIMARY KEY NOT NULL,
	`product_shopify_id` text NOT NULL,
	`title` text NOT NULL,
	`sku` text DEFAULT '' NOT NULL,
	`price` real NOT NULL,
	`compare_at_price` real,
	`inventory_quantity` integer DEFAULT 0 NOT NULL,
	`barcode` text DEFAULT '' NOT NULL,
	`synced_at` text NOT NULL,
	`last_price_check` text,
	`last_market_price` real,
	FOREIGN KEY (`product_shopify_id`) REFERENCES `products`(`shopify_id`) ON UPDATE no action ON DELETE no action
);
