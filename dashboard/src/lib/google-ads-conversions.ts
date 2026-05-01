import "server-only";
import { createHash } from "node:crypto";
import { getAccessToken, type GoogleAdsConfig } from "./google-ads";

const API_VERSION = "v21";
const BASE_URL = `https://googleads.googleapis.com/${API_VERSION}`;

export interface UserIdentifier {
  hashedEmail?: string;
  hashedPhoneNumber?: string;
}

interface ConversionBase {
  conversionActionId: string;
  conversionDateTime: string; // "YYYY-MM-DD HH:MM:SS+00:00"
  conversionValue: number;
  currencyCode: string;
  orderId: string;
  validateOnly?: boolean;
}

export interface ClickConversionParams extends ConversionBase {
  gclid: string;
  userIdentifiers?: UserIdentifier[];
}

export interface EnhancedConversionParams extends ConversionBase {
  userIdentifiers: UserIdentifier[];
}

export interface UploadResult {
  success: boolean;
  rawResponse: unknown;
  error?: string;
  partialFailure?: unknown;
}

export function hashIdentifier(value: string): string {
  return createHash("sha256").update(value.trim().toLowerCase()).digest("hex");
}

export function normalizePhone(phone: string): string {
  const digits = phone.replace(/[^\d+]/g, "");
  if (digits.startsWith("+")) return digits;
  if (digits.length === 10) return `+1${digits}`;
  if (digits.length === 11 && digits.startsWith("1")) return `+${digits}`;
  return digits.startsWith("+") ? digits : `+${digits}`;
}

export function formatConversionDateTime(d: Date | string): string {
  const date = typeof d === "string" ? new Date(d) : d;
  const pad = (n: number) => String(n).padStart(2, "0");
  const yyyy = date.getUTCFullYear();
  const mm = pad(date.getUTCMonth() + 1);
  const dd = pad(date.getUTCDate());
  const hh = pad(date.getUTCHours());
  const mi = pad(date.getUTCMinutes());
  const ss = pad(date.getUTCSeconds());
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}:${ss}+00:00`;
}

async function postUpload(
  config: GoogleAdsConfig,
  body: Record<string, unknown>
): Promise<UploadResult> {
  try {
    const accessToken = await getAccessToken(config);
    const customerId = config.customerId.replace(/-/g, "");

    const headers: Record<string, string> = {
      Authorization: `Bearer ${accessToken}`,
      "developer-token": config.developerToken,
      "Content-Type": "application/json",
    };
    if (config.loginCustomerId) {
      headers["login-customer-id"] = config.loginCustomerId.replace(/-/g, "");
    }

    const resp = await fetch(
      `${BASE_URL}/customers/${customerId}:uploadClickConversions`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      }
    );

    const text = await resp.text();
    let parsed: unknown = text;
    try {
      parsed = JSON.parse(text);
    } catch {
      // leave as text
    }

    if (!resp.ok) {
      return {
        success: false,
        rawResponse: parsed,
        error: `${resp.status} ${typeof parsed === "string" ? parsed : JSON.stringify(parsed)}`,
      };
    }

    const partialFailure = (parsed as { partialFailureError?: unknown })?.partialFailureError;
    if (partialFailure) {
      return { success: false, rawResponse: parsed, error: "partial_failure", partialFailure };
    }

    return { success: true, rawResponse: parsed };
  } catch (err) {
    return { success: false, rawResponse: null, error: String(err) };
  }
}

export async function uploadClickConversion(
  config: GoogleAdsConfig,
  params: ClickConversionParams
): Promise<UploadResult> {
  const customerId = config.customerId.replace(/-/g, "");
  const conversion: Record<string, unknown> = {
    conversionAction: `customers/${customerId}/conversionActions/${params.conversionActionId}`,
    gclid: params.gclid,
    conversionDateTime: params.conversionDateTime,
    conversionValue: params.conversionValue,
    currencyCode: params.currencyCode,
    orderId: params.orderId,
  };
  if (params.userIdentifiers?.length) {
    conversion.userIdentifiers = params.userIdentifiers;
  }

  return postUpload(config, {
    conversions: [conversion],
    partialFailure: true,
    validateOnly: params.validateOnly ?? false,
  });
}

export async function uploadEnhancedConversion(
  config: GoogleAdsConfig,
  params: EnhancedConversionParams
): Promise<UploadResult> {
  if (!params.userIdentifiers.length) {
    return {
      success: false,
      rawResponse: null,
      error: "uploadEnhancedConversion requires at least one userIdentifier",
    };
  }

  const customerId = config.customerId.replace(/-/g, "");
  const conversion = {
    conversionAction: `customers/${customerId}/conversionActions/${params.conversionActionId}`,
    conversionDateTime: params.conversionDateTime,
    conversionValue: params.conversionValue,
    currencyCode: params.currencyCode,
    orderId: params.orderId,
    userIdentifiers: params.userIdentifiers,
  };

  return postUpload(config, {
    conversions: [conversion],
    partialFailure: true,
    validateOnly: params.validateOnly ?? false,
  });
}
