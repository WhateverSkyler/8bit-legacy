import { NextRequest, NextResponse } from "next/server";
import { generateSocialPosts } from "@/lib/python-bridge";

// POST /api/social/generate — generate social media posts via Python script
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const batch = body.batch ?? 10;
    const type = body.type;

    const posts = await generateSocialPosts(batch, type);

    return NextResponse.json({ posts, count: posts.length });
  } catch (error) {
    console.error("Social generation error:", error);
    return NextResponse.json(
      { error: "Failed to generate social posts" },
      { status: 500 }
    );
  }
}
