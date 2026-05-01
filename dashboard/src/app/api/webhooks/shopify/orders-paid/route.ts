import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db } from "@db/index";
import { googleAdsConversionUploads } from "@db/schema";
import { verifyShopifyHmac } from "@/lib/shopify-webhook";
import { getEnv, getGoogleAdsConfig } from "@/lib/config";
import {
  uploadClickConversion,
  uploadEnhancedConversion,
  hashIdentifier,
  normalizePhone,
  formatConversionDateTime,
  type UserIdentifier,
  type UploadResult,
} from "@/lib/google-ads-conversions";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PURCHASE_CONVERSION_ACTION_ID =
  getEnv("GOOGLE_ADS_CONVERSION_ACTION_PURCHASE") || "7590907627";

interface NoteAttribute {
  name?: string;
  value?: string;
}

function findAttr(attrs: NoteAttribute[] | undefined, key: string): string | null {
  if (!attrs) return null;
  const lc = key.toLowerCase();
  for (const a of attrs) {
    if (typeof a?.name === "string" && a.name.toLowerCase() === lc) {
      return typeof a.value === "string" ? a.value : null;
    }
  }
  return null;
}

interface ShopifyOrderPayload {
  id: number | string;
  name?: string;
  total_price?: string;
  currency?: string;
  email?: string | null;
  phone?: string | null;
  contact_email?: string | null;
  customer?: { email?: string | null; phone?: string | null } | null;
  processed_at?: string;
  created_at?: string;
  note_attributes?: NoteAttribute[];
}

async function processOrderPaid(order: ShopifyOrderPayload): Promise<void> {
  const orderId = String(order.id);
  if (!orderId) return;

  const total = parseFloat(order.total_price ?? "0");
  if (!Number.isFinite(total) || total <= 0) {
    console.log(`[orders-paid] order ${orderId} has zero/invalid total, skipping`);
    return;
  }

  const currency = order.currency || "USD";
  const conversionDateTime = formatConversionDateTime(
    order.processed_at || order.created_at || new Date()
  );

  const gclid =
    findAttr(order.note_attributes, "_gclid") ||
    findAttr(order.note_attributes, "gclid");
  const gbraid = findAttr(order.note_attributes, "_gbraid");
  const wbraid = findAttr(order.note_attributes, "_wbraid");

  const email = (order.email || order.contact_email || order.customer?.email || "").trim();
  const phoneRaw = (order.phone || order.customer?.phone || "").trim();

  const userIdentifiers: UserIdentifier[] = [];
  let hashedEmail: string | null = null;
  let hashedPhone: string | null = null;
  if (email) {
    hashedEmail = hashIdentifier(email);
    userIdentifiers.push({ hashedEmail });
  }
  if (phoneRaw) {
    hashedPhone = hashIdentifier(normalizePhone(phoneRaw));
    userIdentifiers.push({ hashedPhoneNumber: hashedPhone });
  }

  const conversionType = gclid || gbraid || wbraid ? "click" : "enhanced";

  const insertResult = db
    .insert(googleAdsConversionUploads)
    .values({
      shopifyOrderId: orderId,
      shopifyOrderNumber: order.name ?? null,
      conversionType,
      gclid: gclid || gbraid || wbraid || null,
      hashedEmail,
      hashedPhone,
      conversionValue: total,
      currencyCode: currency,
      conversionDateTime,
      uploadStatus: "pending",
      attemptCount: 0,
      createdAt: new Date().toISOString(),
    })
    .onConflictDoNothing({ target: googleAdsConversionUploads.shopifyOrderId })
    .run();

  if (insertResult.changes === 0) {
    console.log(`[orders-paid] order ${orderId} already processed, skipping`);
    return;
  }

  if (conversionType === "enhanced" && userIdentifiers.length === 0) {
    db.update(googleAdsConversionUploads)
      .set({
        uploadStatus: "failed",
        errorMessage: "no gclid and no email/phone identifiers",
        attemptCount: 1,
        uploadedAt: new Date().toISOString(),
      })
      .where(eq(googleAdsConversionUploads.shopifyOrderId, orderId))
      .run();
    return;
  }

  const config = getGoogleAdsConfig();
  const validateOnly = getEnv("GOOGLE_ADS_VALIDATE_ONLY") === "true";

  let result: UploadResult;
  if (conversionType === "click") {
    result = await uploadClickConversion(config, {
      conversionActionId: PURCHASE_CONVERSION_ACTION_ID,
      gclid: (gclid || gbraid || wbraid) as string,
      conversionDateTime,
      conversionValue: total,
      currencyCode: currency,
      orderId,
      userIdentifiers: userIdentifiers.length ? userIdentifiers : undefined,
      validateOnly,
    });
  } else {
    result = await uploadEnhancedConversion(config, {
      conversionActionId: PURCHASE_CONVERSION_ACTION_ID,
      conversionDateTime,
      conversionValue: total,
      currencyCode: currency,
      orderId,
      userIdentifiers,
      validateOnly,
    });
  }

  db.update(googleAdsConversionUploads)
    .set({
      uploadStatus: result.success ? "success" : "failed",
      googleAdsResponse: JSON.stringify(result.rawResponse).slice(0, 8000),
      errorMessage: result.error ?? null,
      attemptCount: 1,
      uploadedAt: new Date().toISOString(),
    })
    .where(eq(googleAdsConversionUploads.shopifyOrderId, orderId))
    .run();

  console.log(
    `[orders-paid] order ${orderId} ${conversionType} upload ` +
      `${result.success ? "OK" : "FAIL"}${validateOnly ? " (validateOnly)" : ""}` +
      (result.error ? ` — ${result.error}` : "")
  );
}

export async function POST(req: NextRequest): Promise<Response> {
  const rawBody = await req.text();
  const hmac = req.headers.get("x-shopify-hmac-sha256");
  const topic = req.headers.get("x-shopify-topic");
  const secret = getEnv("SHOPIFY_WEBHOOK_SECRET");

  if (!secret) {
    console.error("[orders-paid] SHOPIFY_WEBHOOK_SECRET not configured");
    return new NextResponse("not configured", { status: 503 });
  }

  if (!verifyShopifyHmac(rawBody, hmac, secret)) {
    console.warn("[orders-paid] invalid hmac");
    return new NextResponse("invalid hmac", { status: 401 });
  }

  if (topic !== "orders/paid") {
    return new NextResponse("ok", { status: 200 });
  }

  let order: ShopifyOrderPayload;
  try {
    order = JSON.parse(rawBody) as ShopifyOrderPayload;
  } catch (err) {
    console.error("[orders-paid] invalid JSON", err);
    return new NextResponse("ok", { status: 200 });
  }

  // Fire-and-forget: respond 200 quickly so Shopify doesn't retry.
  processOrderPaid(order).catch((err) => {
    console.error("[orders-paid] processing failed", err);
  });

  return new NextResponse("ok", { status: 200 });
}
