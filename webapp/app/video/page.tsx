"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check, Heart, Play, Share2 } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { VideoPlayer } from "@/components/VideoPlayer";
import { UploadModal } from "@/components/UploadModal";
import { Comment, Video } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { fetchVideoDetail, mapCatalogItemToVideo } from "@/lib/catalog-api";
import { fetchPlaybackSession, PlaybackSession } from "@/lib/playback-api";

function formatViews(views: number): string {
  if (views >= 1_000_000) {
    return `${(views / 1_000_000).toFixed(1)}M views`;
  }
  if (views >= 1_000) {
    return `${(views / 1_000).toFixed(1)}k views`;
  }
  return `${views} ${views === 1 ? "view" : "views"}`;
}

function VideoPageContent() {
  const searchParams = useSearchParams();
  const videoId = searchParams.get("id");

  const [video, setVideo] = useState<Video | null>(null);
  const [relatedVideos, setRelatedVideos] = useState<Video[]>([]);
  const [playbackSession, setPlaybackSession] = useState<PlaybackSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const { user } = useAuth();
  const [likes, setLikes] = useState(0);
  const [views, setViews] = useState(0);
  const [isLiked, setIsLiked] = useState(false);
  const [copied, setCopied] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Load real video data and playback session
  useEffect(() => {
    if (!videoId) {
      setNotFound(true);
      setIsLoading(false);
      return;
    }

    let isCancelled = false;

    async function loadData() {
      setIsLoading(true);
      setNotFound(false);

      try {
        // 1. Fetch catalog details
        const detail = await fetchVideoDetail(videoId!);
        if (isCancelled) return;

        if (detail && detail.video) {
          const mapped = mapCatalogItemToVideo(detail.video);
          setVideo(mapped);
          setLikes(mapped.likes || 0);
          setViews(mapped.views || 0);

          if (detail.related_videos) {
            setRelatedVideos(detail.related_videos.map(mapCatalogItemToVideo));
          }
        } else {
          setNotFound(true);
        }
      } catch (err) {
        console.error("Error loading video details:", err);
        if (!isCancelled) setNotFound(true);
      }

      // 2. Fetch playback session
      try {
        const session = await fetchPlaybackSession(videoId!);
        if (!isCancelled && session) {
          setPlaybackSession(session);
          if (session.views_count) {
            setViews(session.views_count);
          }
        }
      } catch (err) {
        console.error("Error initiating playback session:", err);
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    loadData();

    return () => {
      isCancelled = true;
    };
  }, [videoId]);

  const handleLike = () => {
    if (isLiked) {
      setLikes((prev) => Math.max(0, prev - 1));
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
        author: user?.username || "You",
        handle: user ? `@${user.username}` : "@you",
        avatar: "",
        content: newComment.trim(),
        timestamp: "Just now",
        likes: 0,
      },
      ...comments,
    ]);
    setNewComment("");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black text-neutral-200 flex flex-col font-sans">
        <Navbar onOpenUpload={() => setIsUploadOpen(true)} />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
            <div className="lg:col-span-8 space-y-4">
              <div className="aspect-video w-full rounded-lg bg-neutral-900 animate-pulse" />
              <div className="h-6 w-3/4 rounded bg-neutral-900 animate-pulse" />
              <div className="h-4 w-1/3 rounded bg-neutral-900 animate-pulse" />
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (notFound || !video) {
    return (
      <div className="min-h-screen bg-black text-neutral-200 flex flex-col font-sans">
        <Navbar onOpenUpload={() => setIsUploadOpen(true)} />
        <main className="mx-auto flex flex-1 flex-col items-center justify-center px-4 py-16 text-center">
          <h2 className="text-base font-semibold text-neutral-100">Video not found</h2>
          <p className="mt-1 text-xs text-neutral-500 max-w-sm">
            This video may have been removed, or the link may be invalid.
          </p>
          <Link
            href="/"
            className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-xs text-neutral-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Catalog</span>
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-neutral-200 flex flex-col font-sans">
      <Navbar onOpenUpload={() => setIsUploadOpen(true)} />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Main Content (8 cols) */}
          <div className="lg:col-span-8">
            <VideoPlayer
              key={video.id}
              video={video}
              streamUrl={playbackSession?.playback_url}
              sessionId={playbackSession?.session_id}
              resumePosition={playbackSession?.resume_position_seconds}
              onViewCountUpdate={(newCount) => setViews(newCount)}
            />

            {/* Video Meta */}
            <div className="mt-4">
              <h1 className="text-base sm:text-lg font-medium text-neutral-100">
                {video.title}
              </h1>

              <div className="mt-2 flex flex-wrap items-center justify-between gap-3 border-b border-neutral-900 pb-4 text-xs text-neutral-500">
                <div className="flex items-center flex-wrap gap-2">
                  <span className="text-neutral-300 font-medium">
                    {video.channel.name}
                  </span>
                  <span>·</span>
                  <span>{formatViews(views)}</span>
                  <span>·</span>
                  <span>{video.uploadedAt}</span>
                  {playbackSession?.stream_type === "hls" && (
                    <>
                      <span>·</span>
                      <span className="inline-flex items-center rounded bg-neutral-900 px-1.5 py-0.5 text-[10px] font-mono text-neutral-300 border border-neutral-800">
                        HLS ABR
                      </span>
                    </>
                  )}
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
              {video.description && (
                <p className="mt-4 text-xs text-neutral-400 leading-relaxed whitespace-pre-line">
                  {video.description}
                </p>
              )}

              {/* Comments */}
              <div className="mt-8 border-t border-neutral-900 pt-6">
                <h3 className="text-sm font-medium text-neutral-200 mb-4">
                  {comments.length} Comments
                </h3>

                {/* Add comment */}
                <form onSubmit={handleAddComment} className="flex gap-2 mb-6">
                  <input
                    type="text"
                    placeholder="Add a comment..."
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    className="flex-1 rounded-md border border-neutral-800 bg-black px-3 py-1.5 text-xs text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={!newComment.trim()}
                    className="rounded-md bg-neutral-100 px-3 py-1.5 text-xs font-medium text-black hover:bg-white disabled:opacity-40 transition-colors"
                  >
                    Comment
                  </button>
                </form>

                {/* Comment list */}
                {comments.length > 0 ? (
                  <div className="space-y-4">
                    {comments.map((comment) => (
                      <div key={comment.id} className="flex gap-3 text-xs">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-800 text-[10px] font-semibold text-neutral-300">
                          {comment.author.slice(0, 1).toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-neutral-300">
                              {comment.author}
                            </span>
                            <span className="text-[10px] text-neutral-600">
                              {comment.timestamp}
                            </span>
                          </div>
                          <p className="mt-1 text-neutral-400 leading-relaxed">
                            {comment.content}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-neutral-600">
                    No comments yet. Be the first to share your thoughts!
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Related Videos Sidebar (4 cols) */}
          <div className="lg:col-span-4">
            <h3 className="text-xs font-medium text-neutral-400 mb-4 uppercase tracking-wider">
              More from Catalog
            </h3>
            {relatedVideos.length > 0 ? (
              <div className="space-y-3">
                {relatedVideos.map((item) => (
                  <Link
                    key={item.id}
                    href={`/video?id=${item.id}`}
                    className="group flex gap-3 rounded-lg p-1.5 -mx-1.5 hover:bg-neutral-900/40 transition-colors"
                  >
                    <div className="relative aspect-video w-32 shrink-0 overflow-hidden rounded bg-neutral-950 border border-neutral-800">
                      {item.thumbnail ? (
                        <img
                          src={item.thumbnail}
                          alt={item.title}
                          className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-neutral-900 text-neutral-500">
                          <Play className="h-4 w-4 fill-current" />
                        </div>
                      )}
                      <div className="absolute bottom-1 right-1 rounded bg-black/80 px-1 py-0.5 text-[9px] font-mono text-neutral-300">
                        {item.duration || "0:00"}
                      </div>
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-neutral-200 line-clamp-2 leading-snug group-hover:text-white">
                        {item.title}
                      </p>
                      <p className="mt-1 text-[11px] text-neutral-500 truncate">
                        {item.channel.name}
                      </p>
                      <p className="text-[10px] text-neutral-600">
                        {formatViews(item.views)}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-xs text-neutral-600">No other videos in this category yet.</p>
            )}
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
        <div className="min-h-screen bg-black flex items-center justify-center text-xs text-neutral-500">
          Loading player...
        </div>
      }
    >
      <VideoPageContent />
    </Suspense>
  );
}
