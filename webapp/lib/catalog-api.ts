import { Video } from "./types";

export interface CatalogVideoItem {
  id: string;
  title: string;
  description: string | null;
  category: string;
  thumbnail_url: string | null;
  duration_seconds: number;
  duration: string;
  width: number | null;
  height: number | null;
  resolution: "4K" | "1440p" | "1080p" | "720p";
  views_count: number;
  likes_count: number;
  status: string;
  hls_status: string | null;
  created_at: string;
  uploaded_at: string;
  channel: {
    id: string;
    name: string;
    handle: string;
    avatar: string;
    subscribers: string;
    verified: boolean;
  };
}

export interface CatalogResponse {
  items: CatalogVideoItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface CategoryItem {
  name: string;
  video_count: number;
}

export function mapCatalogItemToVideo(item: CatalogVideoItem): Video {
  return {
    id: item.id,
    title: item.title,
    description: item.description || "",
    thumbnail:
      item.thumbnail_url ||
      "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1280&q=80",
    videoUrl: `/video?id=${item.id}`,
    duration: item.duration || "0:00",
    durationSeconds: item.duration_seconds || 0,
    views: item.views_count || 0,
    uploadedAt: item.uploaded_at || "Recent",
    likes: item.likes_count || 0,
    channel: {
      name: item.channel.name,
      handle: item.channel.handle,
      avatar: item.channel.avatar,
      subscribers: item.channel.subscribers || "1K",
      verified: item.channel.verified || false,
    },
    category: item.category || "General",
    resolution: item.resolution || "1080p",
    codec: "H.264 / AAC",
    bitrate: "2800 kbps",
    fps: 30,
    edgePoP: "Edge POP",
    tags: [item.category || "General"],
  };
}

export async function fetchCatalogVideos(params?: {
  category?: string;
  q?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<CatalogResponse> {
  const query = new URLSearchParams();
  if (params?.category && params.category !== "All") query.set("category", params.category);
  if (params?.q) query.set("q", params.q);
  if (params?.sort) query.set("sort", params.sort);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const url = `/api/catalog/videos${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch catalog: ${res.status}`);
  }
  return res.json();
}

export async function fetchVideoDetail(videoId: string): Promise<{
  video: CatalogVideoItem;
  related_videos: CatalogVideoItem[];
}> {
  const res = await fetch(`/api/catalog/videos/${videoId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch video detail: ${res.status}`);
  }
  return res.json();
}

export async function fetchCategories(): Promise<{ categories: CategoryItem[] }> {
  const res = await fetch("/api/catalog/categories");
  if (!res.ok) {
    throw new Error(`Failed to fetch categories: ${res.status}`);
  }
  return res.json();
}
