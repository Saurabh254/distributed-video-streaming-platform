"use client";

import React, { useState, useMemo } from "react";
import { Navbar } from "@/components/Navbar";
import { VideoCard } from "@/components/VideoCard";
import { UploadModal } from "@/components/UploadModal";
import { CATEGORIES, MOCK_VIDEOS } from "@/lib/data";

export default function DashboardPage() {
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Filter videos
  const filteredVideos = useMemo(() => {
    return MOCK_VIDEOS.filter((video) => {
      const matchesCategory =
        selectedCategory === "All" || video.category === selectedCategory;
      const matchesSearch =
        searchQuery.trim() === "" ||
        video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        video.channel.name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [selectedCategory, searchQuery]);

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

        {/* Pure Video Grid */}
        {filteredVideos.length > 0 ? (
          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {filteredVideos.map((video) => (
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
