"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Plus, Video as VideoIcon } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { VideoCard } from "@/components/VideoCard";
import { UploadModal } from "@/components/UploadModal";
import { Video } from "@/lib/types";
import {
  fetchCatalogVideos,
  fetchCategories,
  mapCatalogItemToVideo,
} from "@/lib/catalog-api";

export default function DashboardPage() {
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [categories, setCategories] = useState<string[]>(["All"]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch real categories from database
  useEffect(() => {
    async function loadCategories() {
      try {
        const res = await fetchCategories();
        if (res.categories && res.categories.length > 0) {
          const names = res.categories
            .map((c) => c.name)
            .filter((name) => name && name.trim() !== "");
          setCategories(["All", ...names]);
        }
      } catch (err) {
        console.debug("Could not load categories:", err);
      }
    }
    loadCategories();
  }, []);

  // Fetch real videos from catalog service
  const loadVideos = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchCatalogVideos({
        category: selectedCategory === "All" ? undefined : selectedCategory,
        q: searchQuery.trim() || undefined,
        limit: 50,
      });
      if (data.items) {
        setVideos(data.items.map(mapCatalogItemToVideo));
      } else {
        setVideos([]);
      }
    } catch (err) {
      console.error("Failed to load catalog videos:", err);
      setVideos([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, searchQuery]);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  return (
    <div className="min-h-screen bg-black text-neutral-200 flex flex-col font-sans">
      {/* Header */}
      <Navbar
        onOpenUpload={() => setIsUploadOpen(true)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {/* Dynamic Categories / Filters */}
        <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-6 border-b border-neutral-900 no-scrollbar">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`rounded-md px-2.5 py-1 text-xs transition-colors shrink-0 ${
                selectedCategory === category
                  ? "bg-neutral-800 text-white font-medium"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {category}
            </button>
          ))}
        </div>

        {/* Video Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="animate-pulse space-y-3">
                <div className="aspect-video w-full rounded-lg bg-neutral-900" />
                <div className="h-4 w-3/4 rounded bg-neutral-900" />
                <div className="h-3 w-1/2 rounded bg-neutral-900" />
              </div>
            ))}
          </div>
        ) : videos.length > 0 ? (
          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        ) : (
          <div className="py-24 flex flex-col items-center justify-center text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-neutral-900 text-neutral-500 mb-3">
              <VideoIcon className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-medium text-neutral-300">No videos found</h3>
            <p className="mt-1 text-xs text-neutral-500 max-w-sm">
              {searchQuery
                ? `No videos matched "${searchQuery}". Try a different keyword.`
                : "No uploaded videos in this category yet. Be the first to share one!"}
            </p>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-4 flex items-center gap-1.5 rounded-md bg-neutral-100 px-3 py-1.5 text-xs font-medium text-black hover:bg-white transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Upload Video</span>
            </button>
          </div>
        )}
      </main>

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => {
          setIsUploadOpen(false);
          loadVideos();
        }}
      />
    </div>
  );
}
