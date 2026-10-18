"use client";

import React, { useState, useMemo, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import { VideoCard } from "@/components/VideoCard";
import { UploadModal } from "@/components/UploadModal";
import { CATEGORIES, MOCK_VIDEOS } from "@/lib/data";
import { Video } from "@/lib/types";
import { fetchCatalogVideos, mapCatalogItemToVideo } from "@/lib/catalog-api";

export default function DashboardPage() {
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [catalogVideos, setCatalogVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCancelled = false;
    async function loadCatalog() {
      try {
        setIsLoading(true);
        const data = await fetchCatalogVideos({
          category: selectedCategory === "All" ? undefined : selectedCategory,
          q: searchQuery.trim() || undefined,
        });
        if (!isCancelled && data.items && data.items.length > 0) {
          setCatalogVideos(data.items.map(mapCatalogItemToVideo));
        } else if (!isCancelled) {
          setCatalogVideos([]);
        }
      } catch (err) {
        console.debug("Catalog service fetch error, falling back to mock:", err);
        if (!isCancelled) setCatalogVideos([]);
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    loadCatalog();
    return () => {
      isCancelled = true;
    };
  }, [selectedCategory, searchQuery]);

  // Combined video display: real catalog videos prioritized, mock videos as fallback if empty
  const displayVideos = useMemo(() => {
    if (catalogVideos.length > 0) {
      return catalogVideos;
    }

    // Fallback to MOCK_VIDEOS if catalog service has 0 videos
    return MOCK_VIDEOS.filter((video) => {
      const matchesCategory =
        selectedCategory === "All" || video.category === selectedCategory;
      const matchesSearch =
        searchQuery.trim() === "" ||
        video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        video.channel.name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [catalogVideos, selectedCategory, searchQuery]);

  return (
    <div className="min-h-screen bg-black text-neutral-200 flex flex-col font-sans">
      {/* Minimal Header */}
      <Navbar
        onOpenUpload={() => setIsUploadOpen(true)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {/* Minimal Categories / Filters */}
        <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-6 border-b border-neutral-900 no-scrollbar">
          {CATEGORIES.map((category) => (
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
        {isLoading && catalogVideos.length === 0 ? (
          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="animate-pulse space-y-3">
                <div className="aspect-video w-full rounded-lg bg-neutral-900" />
                <div className="h-4 w-3/4 rounded bg-neutral-900" />
                <div className="h-3 w-1/2 rounded bg-neutral-900" />
              </div>
            ))}
          </div>
        ) : displayVideos.length > 0 ? (
          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {displayVideos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        ) : (
          <div className="py-20 text-center text-xs text-neutral-500">
            No videos found.
          </div>
        )}
      </main>

      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
    </div>
  );
}
