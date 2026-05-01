import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";

export function verifyShopifyHmac(
  rawBody: string,
  hmacHeader: string | null | undefined,
  secret: string
): boolean {
  if (!hmacHeader || !secret) return false;
  const digest = createHmac("sha256", secret).update(rawBody, "utf8").digest();
  let got: Buffer;
  try {
    got = Buffer.from(hmacHeader, "base64");
  } catch {
    return false;
  }
  if (digest.length !== got.length) return false;
  return timingSafeEqual(digest, got);
}
