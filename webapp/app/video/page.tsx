"use client";

import React, { useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Heart, Share2, Check } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { VideoPlayer } from "@/components/VideoPlayer";
import { UploadModal } from "@/components/UploadModal";
import { MOCK_VIDEOS, MOCK_COMMENTS } from "@/lib/data";
import { Comment } from "@/lib/types";

function VideoPageContent() {
  const searchParams = useSearchParams();
  const videoId = searchParams.get("id");

  // Selected video
  const currentVideo = useMemo(() => {
    return MOCK_VIDEOS.find((v) => v.id === videoId) || MOCK_VIDEOS[0];
  }, [videoId]);

  // Related videos
  const relatedVideos = useMemo(() => {
    return MOCK_VIDEOS.filter((v) => v.id !== currentVideo.id);
  }, [currentVideo]);

  // State
  const [likes, setLikes] = useState(currentVideo.likes);
  const [isLiked, setIsLiked] = useState(false);
  const [copied, setCopied] = useState(false);
  const [comments, setComments] = useState<Comment[]>(MOCK_COMMENTS);
  const [newComment, setNewComment] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const handleLike = () => {
    if (isLiked) {
      setLikes((prev) => prev - 1);
      setIsLiked(false);
    } else {
      setLikes((prev) => prev + 1);
      setIsLiked(true);
    }
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleAddComment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    setComments([
      {
        id: `c-${Date.now()}`,
        author: "You",
        handle: "@you",
        avatar: "",
        content: newComment.trim(),
        timestamp: "Just now",
        likes: 0,
      },
      ...comments,
    ]);
    setNewComment("");
  };

  return (
    <div className="min-h-screen bg-black text-neutral-200 flex flex-col font-sans">
      <Navbar onOpenUpload={() => setIsUploadOpen(true)} />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Main Content (8 cols) */}
          <div className="lg:col-span-8">
            {/* Pure Minimal Video Player */}
            <VideoPlayer key={currentVideo.id} video={currentVideo} />

            {/* Video Meta */}
            <div className="mt-4">
              <h1 className="text-base sm:text-lg font-medium text-neutral-100">
                {currentVideo.title}
              </h1>

              <div className="mt-2 flex flex-wrap items-center justify-between gap-3 border-b border-neutral-900 pb-4 text-xs text-neutral-500">
                <div>
                  <span className="text-neutral-300 font-medium">
                    {currentVideo.channel.name}
                  </span>
                  <span className="mx-2">·</span>
                  <span>{currentVideo.views.toLocaleString()} views</span>
                  <span className="mx-2">·</span>
                  <span>{currentVideo.uploadedAt}</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleLike}
                    className={`flex items-center gap-1.5 rounded border px-2.5 py-1 transition-colors ${
                      isLiked
                        ? "border-neutral-600 bg-neutral-900 text-white"
                        : "border-neutral-800 bg-neutral-950 text-neutral-400 hover:text-white"
                    }`}
                  >
                    <Heart
                      className={`h-3.5 w-3.5 ${isLiked ? "fill-current text-red-500" : ""}`}
                    />
                    <span>{likes.toLocaleString()}</span>
                  </button>

                  <button
                    onClick={handleShare}
                    className="flex items-center gap-1.5 rounded border border-neutral-800 bg-neutral-950 px-2.5 py-1 text-neutral-400 hover:text-white transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-neutral-200" />
                        <span className="text-neutral-200">Copied</span>
                      </>
                    ) : (
                      <>
                        <Share2 className="h-3.5 w-3.5" />
                        <span>Share</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Description */}
              <p className="mt-4 text-xs text-neutral-400 leading-relaxed">
                {currentVideo.description}
              </p>

              {/* Comments */}
              <div className="mt-10 pt-6 border-t border-neutral-900">
                <h3 className="text-xs font-medium text-neutral-300 mb-4">
                  Comments ({comments.length})
                </h3>

                <form onSubmit={handleAddComment} className="mb-6">
                  <input
                    type="text"
                    placeholder="Add a comment..."
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    className="w-full rounded border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-xs text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
                  />
                </form>

                <div className="space-y-4">
                  {comments.map((comment) => (
                    <div key={comment.id} className="text-xs">
                      <div className="flex items-center gap-2 text-neutral-500 text-[11px]">
                        <span className="font-medium text-neutral-300">
                          {comment.author}
                        </span>
                        <span>·</span>
                        <span>{comment.timestamp}</span>
                      </div>
                      <p className="mt-1 text-neutral-400 leading-normal">
                        {comment.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar (4 cols) */}
          <div className="lg:col-span-4">
            <h3 className="text-xs font-medium text-neutral-400 mb-3">
              Up Next
            </h3>
            <div className="space-y-4">
              {relatedVideos.map((video) => (
                <Link
                  key={video.id}
                  href={`/video?id=${video.id}`}
                  className="group flex gap-3 transition-opacity hover:opacity-80"
                >
                  <div className="relative aspect-video w-32 shrink-0 overflow-hidden rounded bg-neutral-900 border border-neutral-900">
                    <img
                      src={video.thumbnail}
                      alt={video.title}
                      className="h-full w-full object-cover"
                    />
                    <span className="absolute bottom-1 right-1 rounded bg-black/80 px-1 py-0.2 font-mono text-[9px] text-neutral-400">
                      {video.duration}
                    </span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="line-clamp-2 text-xs font-medium text-neutral-300 group-hover:text-white leading-snug">
                      {video.title}
                    </h4>
                    <p className="mt-1 text-[11px] text-neutral-500 truncate">
                      {video.channel.name}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </main>

      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
    </div>
  );
}

export default function VideoPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-black flex items-center justify-center text-neutral-600 text-xs">
          Loading...
        </div>
      }
    >
      <VideoPageContent />
    </Suspense>
  );
}
