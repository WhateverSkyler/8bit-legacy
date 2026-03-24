"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { Sparkles, Copy, Calendar, Globe, Tv, Camera, Check, Loader2 } from "lucide-react";
import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import type { SocialPost } from "@/types/social";

const TEMPLATE_TYPES = [
  { id: "new_arrival", label: "New Arrival", emoji: "\u{1F195}" },
  { id: "deal_of_the_day", label: "Deal of the Day", emoji: "\u{1F525}" },
  { id: "nostalgia", label: "Nostalgia", emoji: "\u{1F579}\uFE0F" },
  { id: "collection_spotlight", label: "Collection Spotlight", emoji: "\u{1F3C6}" },
  { id: "did_you_know", label: "Did You Know?", emoji: "\u{1F4A1}" },
];

const SAMPLE_POSTS: SocialPost[] = [
  {
    type: "new_arrival",
    product: "Super Mario Bros 3",
    caption: "Just added to the shop! Super Mario Bros 3 for only $34.99. Tested, cleaned, and ready to play. Link in bio!\n\n#retrogaming #nes #nintendo #8bitlegacy #retrogames #vintagegaming #gamecollecting #gamecollector",
    productUrl: "",
    imageUrl: "",
    imageSuggestion: "",
    platform: "instagram",
    status: "draft",
  },
  {
    type: "deal_of_the_day",
    product: "Sonic 2",
    caption: "Deal of the Day! Sonic the Hedgehog 2 -- just $14.99. Compare that to what other retro stores charge... we'll wait. 8bitlegacy.com\n\n#retrogaming #segagenesis #sega #8bitlegacy #retrogamedeals #gamingdeals",
    productUrl: "",
    imageUrl: "",
    imageSuggestion: "",
    platform: "tiktok",
    status: "draft",
  },
  {
    type: "nostalgia",
    product: "GoldenEye 007",
    caption: "Remember spending hours playing GoldenEye 007? Those were the days. Relive the memories -- $29.99 at 8bitlegacy.com\n\n#retrogaming #n64 #nintendo64 #nostalgia #90sgaming #8bitlegacy #throwback",
    productUrl: "",
    imageUrl: "",
    imageSuggestion: "",
    platform: "facebook",
    status: "draft",
  },
];

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  instagram: <Camera size={14} />,
  tiktok: <Tv size={14} />,
  facebook: <Globe size={14} />,
};

export default function SocialPage() {
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [posts, setPosts] = useState<SocialPost[]>(SAMPLE_POSTS);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const generateMutation = useMutation({
    mutationFn: async (params: { batch: number; type?: string }) => {
      const resp = await fetch("/api/social/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!resp.ok) throw new Error("Failed to generate posts");
      return resp.json();
    },
    onSuccess: (data) => {
      if (data.posts && data.posts.length > 0) {
        setPosts(data.posts);
      }
    },
  });

  const handleGenerate = () => {
    generateMutation.mutate({
      batch: 20,
      type: selectedType ?? undefined,
    });
  };

  const handleCopy = useCallback(async (caption: string, index: number) => {
    try {
      await navigator.clipboard.writeText(caption);
      setCopiedId(index);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = caption;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopiedId(index);
      setTimeout(() => setCopiedId(null), 2000);
    }
  }, []);

  const filteredPosts = selectedType
    ? posts.filter((p) => p.type === selectedType)
    : posts;

  return (
    <div className="space-y-6">
      <PageHeader title="Social Media" description="Generate and schedule social media posts.">
        <Button
          variant="primary"
          size="sm"
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
        >
          {generateMutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Sparkles size={14} />
          )}
          Generate Batch (20)
        </Button>
      </PageHeader>

      {/* Template Picker */}
      <motion.div
        className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {TEMPLATE_TYPES.map((t) => (
          <motion.div key={t.id} variants={staggerItem}>
            <Card
              hoverable
              className={`cursor-pointer text-center ${selectedType === t.id ? "border-accent-cyan bg-cyan-glow" : ""}`}
              onClick={() => setSelectedType(selectedType === t.id ? null : t.id)}
            >
              <CardContent>
                <span className="text-2xl">{t.emoji}</span>
                <p className="mt-2 text-xs font-semibold text-text-primary">{t.label}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      {/* Generated Posts */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text-primary">
            {selectedType ? `${TEMPLATE_TYPES.find((t) => t.id === selectedType)?.label} Posts` : "All Posts"}
            <span className="ml-2 text-sm font-normal text-text-muted">({filteredPosts.length})</span>
          </h2>
        </div>

        {generateMutation.isPending ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 size={32} className="animate-spin text-accent-cyan mb-4" />
            <p className="text-sm text-text-secondary">Generating posts...</p>
          </div>
        ) : (
          <motion.div className="space-y-4" variants={staggerContainer} initial="hidden" animate="visible" key={selectedType ?? "all"}>
            {filteredPosts.length === 0 ? (
              <p className="text-center text-sm text-text-muted py-8">
                No posts for this type. Click Generate Batch to create some.
              </p>
            ) : (
              filteredPosts.map((post, i) => (
                <motion.div key={i} variants={staggerItem}>
                  <Card>
                    <CardContent>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="info">{post.type.replace(/_/g, " ")}</Badge>
                            {post.platform && (
                              <span className="flex items-center gap-1 text-xs text-text-muted">
                                {PLATFORM_ICONS[post.platform]} {post.platform}
                              </span>
                            )}
                            <Badge variant={post.status === "published" ? "success" : post.status === "scheduled" ? "warning" : "neutral"}>
                              {post.status}
                            </Badge>
                          </div>
                          <p className="text-sm font-medium text-text-primary mb-1">{post.product}</p>
                          <p className="text-xs text-text-secondary whitespace-pre-line leading-relaxed">{post.caption}</p>
                        </div>
                        <div className="flex flex-col gap-2 shrink-0">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Copy caption"
                            onClick={() => handleCopy(post.caption, i)}
                          >
                            {copiedId === i ? <Check size={14} className="text-status-success" /> : <Copy size={14} />}
                          </Button>
                          <Button variant="ghost" size="icon" aria-label="Schedule">
                            <Calendar size={14} />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))
            )}
          </motion.div>
        )}
      </div>

      {generateMutation.isError && (
        <p className="text-center text-xs text-status-error">
          Generation failed (Python script not found or errored). Showing sample posts.
        </p>
      )}
    </div>
  );
}
