export interface Video {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  videoUrl: string;
  duration: string;
  durationSeconds: number;
  views: number;
  uploadedAt: string;
  likes: number;
  channel: {
    name: string;
    handle: string;
    avatar: string;
    subscribers: string;
    verified: boolean;
  };
  category: string;
  resolution: "4K" | "1440p" | "1080p" | "720p";
  codec: string;
  bitrate: string;
  fps: number;
  isLive?: boolean;
  edgePoP: string;
  tags: string[];
  chapters?: { time: string; title: string }[];
}

export interface Comment {
  id: string;
  author: string;
  handle: string;
  avatar: string;
  content: string;
  timestamp: string;
  likes: number;
  isLiked?: boolean;
}

export interface EdgeMetric {
  location: string;
  region: string;
  latencyMs: number;
  status: "optimal" | "nominal" | "degraded";
  activeStreams: number;
  bandwidthGbps: number;
}
