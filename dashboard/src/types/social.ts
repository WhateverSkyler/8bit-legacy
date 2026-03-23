export interface SocialPost {
  id?: number;
  type: string;
  caption: string;
  product: string;
  productUrl: string;
  imageUrl: string;
  imageSuggestion: string;
  scheduledAt?: string;
  publishedAt?: string;
  platform?: "instagram" | "tiktok" | "facebook" | "youtube";
  status: "draft" | "scheduled" | "published";
}
