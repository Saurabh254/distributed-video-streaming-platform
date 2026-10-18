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

export function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diffSec < 60) return "Just now";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
    return date.toLocaleDateString();
  } catch {
    return "Recent";
  }
}

export function mapCatalogItemToVideo(item: CatalogVideoItem): Video {
  return {
    id: item.id,
    title: item.title,
    description: item.description || "",
    thumbnail: item.thumbnail_url || "",
    videoUrl: `/video?id=${item.id}`,
    duration: item.duration || "0:00",
    durationSeconds: item.duration_seconds || 0,
    views: item.views_count || 0,
    uploadedAt: formatRelativeTime(item.created_at),
    likes: item.likes_count || 0,
    channel: {
      name: item.channel.name,
      handle: item.channel.handle,
      avatar:
        item.channel.avatar ||
        `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(
          item.channel.name
        )}`,
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
