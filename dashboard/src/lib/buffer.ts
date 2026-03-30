import "server-only";

const BUFFER_API_BASE = "https://api.bufferapp.com/1";

export interface BufferProfile {
  id: string;
  service: string; // instagram, facebook, twitter, etc.
  serviceUsername: string;
  avatar: string;
}

export interface BufferPostResponse {
  success: boolean;
  bufferId?: string;
  message?: string;
}

export interface BufferAnalytics {
  likes: number;
  comments: number;
  shares: number;
  clicks: number;
  reach: number;
}

/**
 * Fetch connected social profiles from Buffer.
 */
export async function getBufferProfiles(
  accessToken: string
): Promise<BufferProfile[]> {
  const resp = await fetch(
    `${BUFFER_API_BASE}/profiles.json?access_token=${accessToken}`
  );

  if (!resp.ok) {
    throw new Error(`Buffer API error: ${resp.status}`);
  }

  const data = await resp.json();

  return (data as any[]).map((p: any) => ({
    id: p.id,
    service: p.service,
    serviceUsername: p.service_username,
    avatar: p.avatar_https || p.avatar,
  }));
}

/**
 * Create/schedule a post on Buffer.
 */
export async function createBufferPost(
  accessToken: string,
  params: {
    profileIds: string[];
    text: string;
    mediaUrl?: string;
    scheduledAt?: string; // ISO 8601
  }
): Promise<BufferPostResponse> {
  const body: Record<string, unknown> = {
    text: params.text,
    profile_ids: params.profileIds,
  };

  if (params.mediaUrl) {
    body.media = { photo: params.mediaUrl };
  }

  if (params.scheduledAt) {
    body.scheduled_at = params.scheduledAt;
  } else {
    body.now = false; // Add to queue
  }

  const resp = await fetch(
    `${BUFFER_API_BASE}/updates/create.json?access_token=${accessToken}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );

  if (!resp.ok) {
    const error = await resp.text();
    return { success: false, message: `Buffer API error: ${resp.status} — ${error}` };
  }

  const data = await resp.json();

  return {
    success: data.success ?? true,
    bufferId: data.updates?.[0]?.id ?? data.update?.id,
    message: data.message,
  };
}

/**
 * Get analytics for a published Buffer post.
 */
export async function getBufferPostAnalytics(
  accessToken: string,
  updateId: string
): Promise<BufferAnalytics> {
  const resp = await fetch(
    `${BUFFER_API_BASE}/updates/${updateId}/interactions.json?access_token=${accessToken}`
  );

  if (!resp.ok) {
    return { likes: 0, comments: 0, shares: 0, clicks: 0, reach: 0 };
  }

  const data = await resp.json();
  const interactions = data.interactions ?? [];

  let likes = 0;
  let comments = 0;
  let shares = 0;

  for (const i of interactions) {
    if (i.type === "like" || i.type === "favorite") likes++;
    else if (i.type === "comment" || i.type === "reply") comments++;
    else if (i.type === "share" || i.type === "retweet" || i.type === "reblog") shares++;
  }

  return {
    likes,
    comments,
    shares,
    clicks: data.total_clicks ?? 0,
    reach: data.reach ?? 0,
  };
}
