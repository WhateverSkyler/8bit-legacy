import "server-only";
import { readFileSync } from "fs";
import { join } from "path";
import type { PricingConfig } from "@/types/pricing";

const PROJECT_ROOT = join(process.cwd(), "..");
const CONFIG_DIR = join(PROJECT_ROOT, "config");

let _pricingConfig: PricingConfig | null = null;

export function getPricingConfig(): PricingConfig {
  if (!_pricingConfig) {
    const raw = readFileSync(join(CONFIG_DIR, "pricing.json"), "utf-8");
    _pricingConfig = JSON.parse(raw) as PricingConfig;
  }
  return _pricingConfig;
}

export function reloadPricingConfig(): PricingConfig {
  _pricingConfig = null;
  return getPricingConfig();
}

export function savePricingConfig(config: PricingConfig): void {
  const { writeFileSync } = require("fs");
  writeFileSync(
    join(CONFIG_DIR, "pricing.json"),
    JSON.stringify(config, null, 2) + "\n",
    "utf-8"
  );
  _pricingConfig = config;
}

export function getEnv(key: string): string {
  return process.env[key] ?? "";
}

export function getShopifyConfig() {
  return {
    storeUrl: getEnv("SHOPIFY_STORE_URL"),
    accessToken: getEnv("SHOPIFY_ACCESS_TOKEN"),
  };
}

export function getEbayConfig() {
  return {
    appId: getEnv("EBAY_APP_ID"),
    certId: getEnv("EBAY_CERT_ID"),
  };
}

export function getGoogleAdsConfig() {
  return {
    developerToken: getEnv("GOOGLE_ADS_DEVELOPER_TOKEN"),
    clientId: getEnv("GOOGLE_ADS_CLIENT_ID"),
    clientSecret: getEnv("GOOGLE_ADS_CLIENT_SECRET"),
    refreshToken: getEnv("GOOGLE_ADS_REFRESH_TOKEN"),
    customerId: getEnv("GOOGLE_ADS_CUSTOMER_ID"),
  };
}

export function getBufferConfig() {
  return {
    accessToken: getEnv("BUFFER_ACCESS_TOKEN"),
  };
}
