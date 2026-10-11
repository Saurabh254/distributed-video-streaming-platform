"use client";

import React from "react";
import Link from "next/link";
import { Video } from "@/lib/types";

interface VideoCardProps {
  video: Video;
}

export function VideoCard({ video }: VideoCardProps) {
  return (
    <Link
      href={`/video?id=${video.id}`}
      className="group flex flex-col transition-opacity hover:opacity-90"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-neutral-900 border border-neutral-900">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="h-full w-full object-cover"
          loading="lazy"
        />
        <span className="absolute bottom-1.5 right-1.5 rounded bg-black/80 px-1.5 py-0.5 font-mono text-[10px] text-neutral-300">
          {video.duration}
        </span>
      </div>

      {/* Details */}
      <div className="mt-2.5">
        <h3 className="line-clamp-2 text-xs font-medium text-neutral-200 group-hover:text-white leading-snug">
          {video.title}
        </h3>
        <p className="mt-1 text-[11px] text-neutral-500">
          {video.channel.name} · {(video.views / 1000).toFixed(0)}k views · {video.uploadedAt}
        </p>
      </div>
    </Link>
  );
}
