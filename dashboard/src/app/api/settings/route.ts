import { NextRequest, NextResponse } from "next/server";
import {
  getPricingConfig,
  savePricingConfig,
  getShopifyConfig,
  getEbayConfig,
  getGoogleAdsConfig,
  getBufferConfig,
} from "@/lib/config";

// GET /api/settings — get all settings
export async function GET() {
  const pricing = getPricingConfig();
  const shopify = getShopifyConfig();
  const ebay = getEbayConfig();
  const googleAds = getGoogleAdsConfig();
  const buffer = getBufferConfig();

  return NextResponse.json({
    pricing,
    connections: {
      shopify: {
        configured: !!(shopify.storeUrl && shopify.accessToken),
        storeUrl: shopify.storeUrl || null,
      },
      ebay: { configured: !!ebay.appId },
      googleAds: {
        configured: !!(googleAds.developerToken && googleAds.customerId),
      },
      buffer: { configured: !!buffer.accessToken },
    },
  });
}

// PUT /api/settings — update pricing config
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();

    if (body.pricing) {
      savePricingConfig(body.pricing);
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Settings save error:", error);
    return NextResponse.json(
      { error: "Failed to save settings" },
      { status: 500 }
    );
  }
}
