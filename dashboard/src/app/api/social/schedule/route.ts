import { NextRequest, NextResponse } from "next/server";
import { db } from "@db/index";
import { socialPosts } from "@db/schema";
import { eq, inArray } from "drizzle-orm";
import { getBufferConfig } from "@/lib/config";
import { createBufferPost, getBufferProfiles } from "@/lib/buffer";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { postIds, profileIds: requestedProfileIds } = body;

    if (!postIds || postIds.length === 0) {
      return NextResponse.json({ error: "No posts selected" }, { status: 400 });
    }

    const config = getBufferConfig();

    // Fetch posts from DB
    const posts = db
      .select()
      .from(socialPosts)
      .where(inArray(socialPosts.id, postIds))
      .all();

    if (posts.length === 0) {
      return NextResponse.json({ error: "No posts found" }, { status: 404 });
    }

    if (!config.accessToken) {
      // Demo mode: just update status in DB
      for (const post of posts) {
        db.update(socialPosts)
          .set({
            status: "scheduled",
            scheduledAt: new Date().toISOString(),
          })
          .where(eq(socialPosts.id, post.id))
          .run();
      }

      return NextResponse.json({
        success: posts.length,
        failed: 0,
        demo: true,
        message: "Posts marked as scheduled (demo mode — no Buffer credentials)",
      });
    }

    // Get Buffer profiles
    let profileIds = requestedProfileIds;
    if (!profileIds || profileIds.length === 0) {
      const profiles = await getBufferProfiles(config.accessToken);
      profileIds = profiles.map((p) => p.id);
    }

    if (profileIds.length === 0) {
      return NextResponse.json(
        { error: "No Buffer profiles found" },
        { status: 400 }
      );
    }

    // Schedule each post
    let successCount = 0;
    let failCount = 0;
    const errors: string[] = [];

    for (const post of posts) {
      const result = await createBufferPost(config.accessToken, {
        profileIds,
        text: post.caption,
        mediaUrl: post.imageUrl || undefined,
      });

      if (result.success && result.bufferId) {
        db.update(socialPosts)
          .set({
            status: "scheduled",
            scheduledAt: new Date().toISOString(),
            bufferId: result.bufferId,
            bufferProfileId: profileIds[0],
          })
          .where(eq(socialPosts.id, post.id))
          .run();
        successCount++;
      } else {
        failCount++;
        errors.push(`Post ${post.id}: ${result.message}`);
      }

      // Rate limit
      await new Promise((r) => setTimeout(r, 200));
    }

    return NextResponse.json({
      success: successCount,
      failed: failCount,
      errors,
    });
  } catch (error) {
    console.error("Social schedule error:", error);
    return NextResponse.json(
      { error: "Failed to schedule posts" },
      { status: 500 }
    );
  }
}
