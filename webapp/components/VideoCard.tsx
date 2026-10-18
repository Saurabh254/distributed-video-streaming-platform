"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Play } from "lucide-react";
import { Video } from "@/lib/types";

interface VideoCardProps {
  video: Video;
}

function formatViews(views: number): string {
  if (views >= 1_000_000) {
    return `${(views / 1_000_000).toFixed(1)}M views`;
  }
  if (views >= 1_000) {
    return `${(views / 1_000).toFixed(1)}k views`;
  }
  return `${views} ${views === 1 ? "view" : "views"}`;
}

export function VideoCard({ video }: VideoCardProps) {
  const [imageError, setImageError] = useState(false);

  return (
    <Link
      href={`/video?id=${video.id}`}
      className="group flex flex-col transition-opacity hover:opacity-95"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-neutral-950 border border-neutral-900 group-hover:border-neutral-800 transition-colors">
        {!imageError && video.thumbnail ? (
          <img
            src={video.thumbnail}
            alt={video.title}
            className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center bg-gradient-to-br from-neutral-950 via-neutral-900 to-black p-4 text-center">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-neutral-800/80 text-neutral-300 mb-2 group-hover:bg-neutral-700 transition-colors">
              <Play className="h-4 w-4 fill-current ml-0.5" />
            </div>
            <span className="text-[11px] font-medium text-neutral-400 line-clamp-1">
              {video.category || "Video"}
            </span>
          </div>
        )}
        <span className="absolute bottom-1.5 right-1.5 rounded bg-black/80 px-1.5 py-0.5 font-mono text-[10px] text-neutral-300">
          {video.duration || "0:00"}
        </span>
      </div>

      {/* Details */}
      <div className="mt-2.5">
        <h3 className="line-clamp-2 text-xs font-medium text-neutral-200 group-hover:text-white leading-snug">
          {video.title}
        </h3>
        <p className="mt-1 text-[11px] text-neutral-500">
          {video.channel.name} · {formatViews(video.views)} · {video.uploadedAt}
        </p>
      </div>
    </Link>
  );
}
