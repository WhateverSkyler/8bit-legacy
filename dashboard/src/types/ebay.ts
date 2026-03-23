export interface EbayListing {
  title: string;
  price: number;
  shipping: number;
  total: number;
  condition: string;
  url: string;
  seller: string;
  sellerFeedback: string;
  imageUrl: string;
}

export interface EbaySearchResult {
  query: string;
  results: EbayListing[];
  shopifyPrice?: number;
  isFallback: boolean;
}
