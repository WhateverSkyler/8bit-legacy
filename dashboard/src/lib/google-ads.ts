import "server-only";

/**
 * Google Ads API client.
 *
 * Uses the Google Ads REST API directly with OAuth2 tokens.
 * The `googleapis` package handles token refresh.
 *
 * Note: Google Ads API requires a developer token, which needs approval.
 * Until approved, this module works with sample data fallbacks.
 */

export interface GoogleAdsConfig {
  developerToken: string;
  clientId: string;
  clientSecret: string;
  refreshToken: string;
  customerId: string;
}

export function isGoogleAdsConfigured(config: GoogleAdsConfig): boolean {
  return !!(config.developerToken && config.customerId && config.refreshToken);
}

const API_VERSION = "v17";
const BASE_URL = `https://googleads.googleapis.com/${API_VERSION}`;

/**
 * Get a fresh OAuth2 access token using the refresh token.
 */
async function getAccessToken(config: GoogleAdsConfig): Promise<string> {
  const resp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: config.clientId,
      client_secret: config.clientSecret,
      refresh_token: config.refreshToken,
      grant_type: "refresh_token",
    }),
  });

  if (!resp.ok) {
    throw new Error(`OAuth2 token refresh failed: ${resp.status}`);
  }

  const data = await resp.json();
  return data.access_token;
}

/**
 * Execute a Google Ads Search query (GAQL).
 */
async function searchGoogleAds(
  config: GoogleAdsConfig,
  query: string
): Promise<any[]> {
  const accessToken = await getAccessToken(config);
  const customerId = config.customerId.replace(/-/g, "");

  const resp = await fetch(
    `${BASE_URL}/customers/${customerId}/googleAds:searchStream`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "developer-token": config.developerToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    }
  );

  if (!resp.ok) {
    const error = await resp.text();
    throw new Error(`Google Ads API error: ${resp.status} — ${error}`);
  }

  const data = await resp.json();
  // searchStream returns an array of result batches
  const results: any[] = [];
  for (const batch of data) {
    if (batch.results) {
      results.push(...batch.results);
    }
  }
  return results;
}

/**
 * Fetch campaign performance for a date range.
 */
export async function getCampaignPerformance(
  config: GoogleAdsConfig,
  startDate: string,
  endDate: string
) {
  const query = `
    SELECT
      campaign.id,
      campaign.name,
      segments.date,
      metrics.impressions,
      metrics.clicks,
      metrics.cost_micros,
      metrics.conversions,
      metrics.conversions_value
    FROM campaign
    WHERE segments.date BETWEEN '${startDate}' AND '${endDate}'
      AND campaign.status = 'ENABLED'
    ORDER BY segments.date DESC
  `;

  const results = await searchGoogleAds(config, query);

  return results.map((r: any) => ({
    date: r.segments.date,
    campaignId: r.campaign.id,
    campaignName: r.campaign.name,
    impressions: parseInt(r.metrics.impressions) || 0,
    clicks: parseInt(r.metrics.clicks) || 0,
    cost: (parseInt(r.metrics.costMicros) || 0) / 1_000_000,
    conversions: Math.round(parseFloat(r.metrics.conversions) || 0),
    conversionValue: parseFloat(r.metrics.conversionsValue) || 0,
  }));
}

/**
 * Fetch shopping product performance.
 */
export async function getProductPerformance(
  config: GoogleAdsConfig,
  startDate: string,
  endDate: string
) {
  const query = `
    SELECT
      segments.product_title,
      segments.product_item_id,
      segments.date,
      metrics.impressions,
      metrics.clicks,
      metrics.cost_micros,
      metrics.conversions,
      metrics.conversions_value
    FROM shopping_performance_view
    WHERE segments.date BETWEEN '${startDate}' AND '${endDate}'
    ORDER BY metrics.clicks DESC
  `;

  const results = await searchGoogleAds(config, query);

  return results.map((r: any) => ({
    date: r.segments.date,
    productId: r.segments.productItemId,
    productTitle: r.segments.productTitle,
    impressions: parseInt(r.metrics.impressions) || 0,
    clicks: parseInt(r.metrics.clicks) || 0,
    cost: (parseInt(r.metrics.costMicros) || 0) / 1_000_000,
    conversions: Math.round(parseFloat(r.metrics.conversions) || 0),
    conversionValue: parseFloat(r.metrics.conversionsValue) || 0,
  }));
}

/**
 * Fetch search term report.
 */
export async function getSearchTermReport(
  config: GoogleAdsConfig,
  startDate: string,
  endDate: string
) {
  const query = `
    SELECT
      search_term_view.search_term,
      campaign.id,
      metrics.impressions,
      metrics.clicks,
      metrics.cost_micros,
      metrics.conversions
    FROM search_term_view
    WHERE segments.date BETWEEN '${startDate}' AND '${endDate}'
      AND metrics.clicks > 0
    ORDER BY metrics.clicks DESC
    LIMIT 500
  `;

  const results = await searchGoogleAds(config, query);

  return results.map((r: any) => ({
    searchTerm: r.searchTermView.searchTerm,
    campaignId: r.campaign.id,
    impressions: parseInt(r.metrics.impressions) || 0,
    clicks: parseInt(r.metrics.clicks) || 0,
    cost: (parseInt(r.metrics.costMicros) || 0) / 1_000_000,
    conversions: Math.round(parseFloat(r.metrics.conversions) || 0),
  }));
}

/**
 * Add a negative keyword to a campaign.
 */
export async function addNegativeKeyword(
  config: GoogleAdsConfig,
  campaignId: string,
  keyword: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const accessToken = await getAccessToken(config);
    const customerId = config.customerId.replace(/-/g, "");

    const resp = await fetch(
      `${BASE_URL}/customers/${customerId}/campaignCriteria:mutate`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "developer-token": config.developerToken,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          operations: [
            {
              create: {
                campaign: `customers/${customerId}/campaigns/${campaignId}`,
                negative: true,
                keyword: {
                  text: keyword,
                  matchType: "BROAD",
                },
              },
            },
          ],
        }),
      }
    );

    if (!resp.ok) {
      const error = await resp.text();
      return { success: false, error };
    }

    return { success: true };
  } catch (err) {
    return { success: false, error: String(err) };
  }
}

/**
 * Pause all enabled campaigns in the account.
 * Called by the circuit breaker when safety conditions are violated.
 */
export async function pauseAllCampaigns(
  config: GoogleAdsConfig
): Promise<{ success: boolean; paused: number; error?: string }> {
  try {
    const accessToken = await getAccessToken(config);
    const customerId = config.customerId.replace(/-/g, "");

    // First, find all enabled campaigns
    const campaigns = await searchGoogleAds(config, `
      SELECT campaign.id, campaign.name, campaign.status
      FROM campaign
      WHERE campaign.status = 'ENABLED'
    `);

    if (campaigns.length === 0) {
      return { success: true, paused: 0 };
    }

    // Pause each campaign
    const operations = campaigns.map((c: any) => ({
      update: {
        resourceName: `customers/${customerId}/campaigns/${c.campaign.id}`,
        status: "PAUSED",
      },
      updateMask: "status",
    }));

    const resp = await fetch(
      `${BASE_URL}/customers/${customerId}/campaigns:mutate`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "developer-token": config.developerToken,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ operations }),
      }
    );

    if (!resp.ok) {
      const error = await resp.text();
      return { success: false, paused: 0, error };
    }

    return { success: true, paused: campaigns.length };
  } catch (err) {
    return { success: false, paused: 0, error: String(err) };
  }
}

/**
 * Enable (unpause) a specific campaign by ID.
 */
export async function enableCampaign(
  config: GoogleAdsConfig,
  campaignId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const accessToken = await getAccessToken(config);
    const customerId = config.customerId.replace(/-/g, "");

    const resp = await fetch(
      `${BASE_URL}/customers/${customerId}/campaigns:mutate`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "developer-token": config.developerToken,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          operations: [
            {
              update: {
                resourceName: `customers/${customerId}/campaigns/${campaignId}`,
                status: "ENABLED",
              },
              updateMask: "status",
            },
          ],
        }),
      }
    );

    if (!resp.ok) {
      const error = await resp.text();
      return { success: false, error };
    }

    return { success: true };
  } catch (err) {
    return { success: false, error: String(err) };
  }
}
