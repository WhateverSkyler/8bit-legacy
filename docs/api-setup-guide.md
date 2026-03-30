# API Setup Guide — 8-Bit Legacy

Complete step-by-step for setting up all API credentials the dashboard needs.
Do them in this order. Shopify is required first; the rest unlock additional features.

---

## 1. Shopify Admin API (Required — everything depends on this)

> **2026 Update:** As of January 1, 2026, legacy custom apps (the old Settings > Apps > Develop apps flow) are deprecated for new apps. You now create apps in the **Dev Dashboard** via a free Shopify Partner account, and use **Client Credentials** to get tokens programmatically.

### Step A: Create a Shopify Partner account (free)

1. Go to **https://partners.shopify.com**
2. Click **"Create and set up a new partner organization"**
3. Organization name: `8-Bit Legacy` (or your name — doesn't matter)
4. When asked "What's your main focus?", pick **"Build apps"**
5. Accept terms — you'll land on the Partner Dashboard

### Step B: Create the app in Dev Dashboard

1. In the Partner Dashboard left sidebar, click **Apps**
2. Click **Create app** (top right)
3. Choose **Start from Dev Dashboard**
4. Name: `8-Bit Legacy Dashboard`
5. Click **Create**

### Step C: Configure API scopes

1. In your new app, go to the **Versions** tab
2. Click **Create version** (or edit the draft)
3. In the **Access** section, add these scopes:
   - `read_products`
   - `write_products`
   - `read_orders`
   - `write_orders`
   - `read_fulfillments`
   - `write_fulfillments`
4. Set the App URL to `http://localhost:3001` (or your VPS URL later)
5. Click **Release**

### Step D: Get your Client ID and Client Secret

1. Go to the **Settings** tab of your app
2. Copy the **Client ID** and **Client Secret**
3. Keep these safe — the Client Secret is sensitive, never commit it

### Step E: Install the app on your store

1. Go to the **Home** tab of your app
2. Scroll down and click **Install app**
3. Select your 8-Bit Legacy Shopify store
4. Confirm the installation

### Step F: Add to .env.local

Create the file if it doesn't exist:
```bash
touch dashboard/.env.local
```

Add:
```
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_CLIENT_ID=your_client_id_here
SHOPIFY_CLIENT_SECRET=your_client_secret_here
```

> **Note:** The old `SHOPIFY_ACCESS_TOKEN` (static `shpat_` token) no longer works for new apps. The dashboard code needs to be updated to use the client credentials grant flow, which exchanges Client ID + Secret for a 24-hour access token automatically. This update will be done once credentials are ready.

### How the new token flow works

Instead of a permanent token, the dashboard will call this on each API request (cached for 24 hours):

```
POST https://{shop}.myshopify.com/admin/oauth/access_token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={client_id}
&client_secret={client_secret}
```

Response:
```json
{
  "access_token": "f85632530bf277ec9ac6f649fc327f17",
  "scope": "write_orders,read_customers",
  "expires_in": 86399
}
```

**References:**
- https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant
- https://shopify.dev/docs/apps/build/dev-dashboard/create-apps-using-dev-dashboard

---

## 2. eBay Browse API (for fulfillment search)

The Browse API lets the dashboard search eBay listings to find the cheapest option when fulfilling orders. You still buy manually — this just automates the searching.

### Step A: Create an eBay Developer account

1. Go to **https://developer.ebay.com**
2. Sign in with your eBay account (the one you use to buy)
3. If you don't have a developer account, click **Register**

### Step B: Create an application

1. Go to **https://developer.ebay.com/my/keys**
2. Click **Create a keyset** (if you don't have one)
3. Application Title: `8-Bit Legacy Finder`
4. Environment: **Production**
5. You'll get:
   - **App ID (Client ID)**
   - **Cert ID (Client Secret)**

### Step C: Generate an OAuth access token

Run this in your terminal (replace YOUR_APP_ID and YOUR_CERT_ID):

```bash
curl -X POST https://api.ebay.com/identity/v1/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic $(echo -n 'YOUR_APP_ID:YOUR_CERT_ID' | base64)" \
  -d "grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope"
```

Copy the `access_token` from the response.

### Step D: Add to .env.local

```
EBAY_APP_ID=the_access_token_you_got
```

> **Note:** This token expires (typically 2 hours). The dashboard gracefully falls back to generating eBay.com search URLs when it expires. For production, the code should be updated to auto-refresh using App ID + Cert ID.

---

## 3. Buffer API (for social media scheduling)

Buffer lets the dashboard auto-schedule social media posts to Instagram, Facebook, and TikTok.

### Step A: Create a Buffer account

1. Go to **https://buffer.com** and sign up (free tier works)
2. Connect your social profiles:
   - Click your avatar > **Channels**
   - Connect Instagram, Facebook, and/or TikTok

### Step B: Create an app and get access token

**Option 1 — Personal Access Token (simplest):**
1. Go to **https://buffer.com/developers/api/oauth**
2. Use the "Quick Start" section to generate a personal access token

**Option 2 — Create an app:**
1. Go to **https://buffer.com/developers/apps/create**
2. App name: `8-Bit Legacy Dashboard`
3. Callback URL: `http://localhost:3001/callback`
4. After creating, go to **https://buffer.com/developers/apps**
5. Click your app to see the **Access Token**

### Step C: Add to .env.local

```
BUFFER_ACCESS_TOKEN=your_token_here
```

---

## 4. Google Ads API (most complex — start early, takes days)

Google Ads automation requires a developer token that needs approval from Google. Start this process early — approval typically takes 1-7 business days.

### Step A: Connect Shopify to Google Merchant Center

1. In Shopify admin, go to **Apps** > search the App Store for **Google & YouTube** (official Shopify app)
2. Install it and connect your Google account
3. Follow the setup wizard to sync your product feed to Google Merchant Center
4. This is required for Google Shopping ads — your products must be in Merchant Center

### Step B: Find your Google Ads Customer ID

1. Go to **https://ads.google.com**
2. Log in with your Google account
3. Your Customer ID is at the top right — looks like `123-456-7890`
4. Write this down

### Step C: Apply for API developer token (1-7 days wait)

1. In Google Ads, click the **wrench icon** (Tools & Settings)
2. Go to **Setup > API Center**
3. If you don't see API Center, accept the API Terms of Service first
4. Click **Apply for a developer token**
5. Fill out:
   - Company name: `8-Bit Legacy`
   - API usage: `Managing my own accounts`
   - Description: `Automated campaign performance reporting and bid optimization for my own Google Shopping campaigns`
6. Submit and wait for approval email
7. Once approved, your **Developer Token** appears on the API Center page

### Step D: Create OAuth2 credentials in Google Cloud

1. Go to **https://console.cloud.google.com**
2. Create a new project: `8-Bit Legacy Ads`
3. Enable the Google Ads API:
   - Go to **APIs & Services > Library**
   - Search `Google Ads API`
   - Click **Enable**
4. Create OAuth credentials:
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth client ID**
   - Application type: **Web application**
   - Name: `8-Bit Legacy Dashboard`
   - Authorized redirect URIs: add `http://localhost:3001/callback`
   - Click **Create**
   - Copy the **Client ID** and **Client Secret**

### Step E: Generate a refresh token

1. Go to **https://developers.google.com/oauthplayground**
2. Click the gear icon (top right) > check **Use your own OAuth credentials**
3. Paste your Client ID and Client Secret from Step D
4. In the left panel, scroll to **Google Ads API v17** and select `https://www.googleapis.com/auth/adwords`
5. Click **Authorize APIs**
6. Sign in and grant access
7. Click **Exchange authorization code for tokens**
8. Copy the **Refresh Token**

### Step F: Add to .env.local

```
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=123-456-7890
```

---

## Complete .env.local Template

When all APIs are set up, your `dashboard/.env.local` should look like:

```bash
# Shopify Admin API (new client credentials flow, 2026+)
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_CLIENT_ID=your_shopify_client_id
SHOPIFY_CLIENT_SECRET=your_shopify_client_secret

# eBay Browse API
EBAY_APP_ID=your_ebay_access_token

# Buffer
BUFFER_ACCESS_TOKEN=your_buffer_token

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=your_dev_token
GOOGLE_ADS_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_google_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_google_refresh_token
GOOGLE_ADS_CUSTOMER_ID=123-456-7890
```

> **IMPORTANT:** This file is gitignored. Never commit API keys.

---

## Status Checklist

- [ ] Shopify Partner account created
- [ ] Shopify app created in Dev Dashboard
- [ ] Shopify app installed on store
- [ ] Shopify Client ID + Secret in .env.local
- [ ] Dashboard code updated for client credentials flow
- [ ] eBay Developer account created
- [ ] eBay app + OAuth token generated
- [ ] eBay token in .env.local
- [ ] Buffer account created + channels connected
- [ ] Buffer access token in .env.local
- [ ] Google Merchant Center connected to Shopify
- [ ] Google Ads developer token applied for
- [ ] Google Ads developer token approved
- [ ] Google Cloud OAuth credentials created
- [ ] Google Ads refresh token generated
- [ ] Google Ads credentials in .env.local
- [ ] Dashboard deployed to VPS
- [ ] Scheduler started
