import { NextResponse } from "next/server";
import { db } from "@db/index";
import { socialPosts } from "@db/schema";
import { isNotNull, desc } from "drizzle-orm";
import { getBufferConfig } from "@/lib/config";
import { getBufferPostAnalytics } from "@/lib/buffer";

export async function GET() {
  try {
    // Get published posts with Buffer IDs
    const posts = db
      .select()
      .from(socialPosts)
      .where(isNotNull(socialPosts.bufferId))
      .orderBy(desc(socialPosts.createdAt))
      .limit(50)
      .all();

    const config = getBufferConfig();

    // If Buffer is configured, refresh engagement data for recent posts
    if (config.accessToken && posts.length > 0) {
      const recentPosts = posts.slice(0, 10); // Only refresh the 10 most recent
      for (const post of recentPosts) {
        if (!post.bufferId) continue;
        try {
          const analytics = await getBufferPostAnalytics(
            config.accessToken,
            post.bufferId
          );
          db.update(socialPosts)
            .set({
              engagementLikes: analytics.likes,
              engagementComments: analytics.comments,
              engagementShares: analytics.shares,
            })
            .where(isNotNull(socialPosts.bufferId))
            .run();
        } catch {
          // Best effort
        }
      }
    }

    // Aggregate stats
    const totalPosts = posts.length;
    const totalLikes = posts.reduce((s, p) => s + (p.engagementLikes ?? 0), 0);
    const totalComments = posts.reduce((s, p) => s + (p.engagementComments ?? 0), 0);
    const totalShares = posts.reduce((s, p) => s + (p.engagementShares ?? 0), 0);

    return NextResponse.json({
      posts: posts.map((p) => ({
        id: p.id,
        type: p.type,
        caption: p.caption,
        product: p.product,
        platform: p.platform,
        status: p.status,
        scheduledAt: p.scheduledAt,
        publishedAt: p.publishedAt,
        engagement: {
          likes: p.engagementLikes ?? 0,
          comments: p.engagementComments ?? 0,
          shares: p.engagementShares ?? 0,
        },
      })),
      summary: {
        totalPosts,
        totalLikes,
        totalComments,
        totalShares,
        totalEngagement: totalLikes + totalComments + totalShares,
      },
    });
  } catch (error) {
    console.error("Social analytics error:", error);
    return NextResponse.json(
      { error: "Failed to fetch social analytics" },
      { status: 500 }
    );
  }
}
