"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { Sparkles, Copy, Calendar, Globe, Tv, Camera } from "lucide-react";
import { useState } from "react";

const TEMPLATE_TYPES = [
  { id: "new_arrival", label: "New Arrival", emoji: "🆕" },
  { id: "deal_of_the_day", label: "Deal of the Day", emoji: "🔥" },
  { id: "nostalgia", label: "Nostalgia", emoji: "🕹️" },
  { id: "collection_spotlight", label: "Collection Spotlight", emoji: "🏆" },
  { id: "did_you_know", label: "Did You Know?", emoji: "💡" },
];

const SAMPLE_POSTS = [
  {
    type: "new_arrival",
    product: "Super Mario Bros 3",
    caption: "Just added to the shop! Super Mario Bros 3 for only $34.99. Tested, cleaned, and ready to play. Link in bio!\n\n#retrogaming #nes #nintendo #8bitlegacy #retrogames #vintagegaming #gamecollecting #gamecollector",
    platform: "instagram",
  },
  {
    type: "deal_of_the_day",
    product: "Sonic 2",
    caption: "Deal of the Day! Sonic the Hedgehog 2 — just $14.99. Compare that to what other retro stores charge... we'll wait. 8bitlegacy.com\n\n#retrogaming #segagenesis #sega #8bitlegacy #retrogamedeals #gamingdeals",
    platform: "tiktok",
  },
  {
    type: "nostalgia",
    product: "GoldenEye 007",
    caption: "Remember spending hours playing GoldenEye 007? Those were the days. Relive the memories — $29.99 at 8bitlegacy.com\n\n#retrogaming #n64 #nintendo64 #nostalgia #90sgaming #8bitlegacy #throwback",
    platform: "facebook",
  },
];

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  instagram: <Camera size={14} />,
  tiktok: <Tv size={14} />,
  facebook: <Globe size={14} />,
};

export default function SocialPage() {
  const [selectedType, setSelectedType] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader title="Social Media" description="Generate and schedule social media posts.">
        <Button variant="primary" size="sm">
          <Sparkles size={14} />
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
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Generated Posts</h2>
        <motion.div className="space-y-4" variants={staggerContainer} initial="hidden" animate="visible">
          {SAMPLE_POSTS.map((post, i) => (
            <motion.div key={i} variants={staggerItem}>
              <Card>
                <CardContent>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="info">{post.type.replace(/_/g, " ")}</Badge>
                        <span className="flex items-center gap-1 text-xs text-text-muted">
                          {PLATFORM_ICONS[post.platform]} {post.platform}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-text-primary mb-1">{post.product}</p>
                      <p className="text-xs text-text-secondary whitespace-pre-line leading-relaxed">{post.caption}</p>
                    </div>
                    <div className="flex flex-col gap-2 shrink-0">
                      <Button variant="ghost" size="icon" aria-label="Copy caption">
                        <Copy size={14} />
                      </Button>
                      <Button variant="ghost" size="icon" aria-label="Schedule">
                        <Calendar size={14} />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
