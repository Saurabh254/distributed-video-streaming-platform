"use client";

import React, { useState, useMemo, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Heart, Share2, Check } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { VideoPlayer } from "@/components/VideoPlayer";
import { UploadModal } from "@/components/UploadModal";
import { MOCK_VIDEOS, MOCK_COMMENTS } from "@/lib/data";
import { Comment, Video } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { fetchVideoDetail, mapCatalogItemToVideo } from "@/lib/catalog-api";
import { fetchPlaybackSession, PlaybackSession } from "@/lib/playback-api";

function VideoPageContent() {
  const searchParams = useSearchParams();
  const videoId = searchParams.get("id");

  const [dbVideo, setDbVideo] = useState<Video | null>(null);
  const [dbRelated, setDbRelated] = useState<Video[]>([]);
  const [playbackSession, setPlaybackSession] = useState<PlaybackSession | null>(null);

  // Fallback to mock video if DB video not found
  const mockFallbackVideo = useMemo(() => {
    return MOCK_VIDEOS.find((v) => v.id === videoId) || MOCK_VIDEOS[0];
  }, [videoId]);

  const currentVideo = dbVideo || mockFallbackVideo;

  const relatedVideos = useMemo(() => {
    if (dbRelated.length > 0) return dbRelated;
    return MOCK_VIDEOS.filter((v) => v.id !== currentVideo.id);
  }, [dbRelated, currentVideo]);

  const { user } = useAuth();
  const [likes, setLikes] = useState(currentVideo.likes);
  const [views, setViews] = useState(currentVideo.views);
  const [isLiked, setIsLiked] = useState(false);
  const [copied, setCopied] = useState(false);
  const [comments, setComments] = useState<Comment[]>(MOCK_COMMENTS);
  const [newComment, setNewComment] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Sync state when current video changes
  useEffect(() => {
    setLikes(currentVideo.likes);
    setViews(currentVideo.views);
  }, [currentVideo]);

  // Load video metadata from catalog and initiate playback session
  useEffect(() => {
    if (!videoId) return;

    let isCancelled = false;

    async function loadData() {
      // 1. Fetch catalog detail
      try {
        const detail = await fetchVideoDetail(videoId!);
        if (!isCancelled && detail?.video) {
          setDbVideo(mapCatalogItemToVideo(detail.video));
          if (detail.related_videos) {
            setDbRelated(detail.related_videos.map(mapCatalogItemToVideo));
          }
        }
      } catch (err) {
        console.debug("Video detail not in catalog service, using fallback:", err);
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
        console.debug("Playback session error, using default stream:", err);
      }
    }

    loadData();

    return () => {
      isCancelled = true;
    };
  }, [videoId]);

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

  return (
    <div className="min-h-screen bg-black text-neutral-200 flex flex-col font-sans">
      <Navbar onOpenUpload={() => setIsUploadOpen(true)} />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Main Content (8 cols) */}
          <div className="lg:col-span-8">
            {/* Pure Minimal Video Player */}
            <VideoPlayer
              key={currentVideo.id}
              video={currentVideo}
              streamUrl={playbackSession?.playback_url}
              sessionId={playbackSession?.session_id}
              resumePosition={playbackSession?.resume_position_seconds}
              onViewCountUpdate={(newCount) => setViews(newCount)}
            />

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
                  <span>{views.toLocaleString()} views</span>
                  <span className="mx-2">·</span>
                  <span>{currentVideo.uploadedAt}</span>
                  {playbackSession?.stream_type === "hls" && (
                    <>
                      <span className="mx-2">·</span>
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
              <p className="mt-4 text-xs text-neutral-400 leading-relaxed">
                {currentVideo.description}
              </p>

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
              </div>
            </div>
          </div>

          {/* Related Videos Sidebar (4 cols) */}
          <div className="lg:col-span-4">
            <h3 className="text-xs font-medium text-neutral-400 mb-4 uppercase tracking-wider">
              Up Next
            </h3>
            <div className="space-y-3">
              {relatedVideos.map((video) => (
                <Link
                  key={video.id}
                  href={`/video?id=${video.id}`}
                  className="group flex gap-3 rounded-lg p-1.5 -mx-1.5 hover:bg-neutral-900/40 transition-colors"
                >
                  <div className="relative aspect-video w-32 shrink-0 overflow-hidden rounded bg-neutral-900 border border-neutral-800">
                    <img
                      src={video.thumbnail}
                      alt={video.title}
                      className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute bottom-1 right-1 rounded bg-black/80 px-1 py-0.5 text-[9px] font-mono text-neutral-300">
                      {video.duration}
                    </div>
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-neutral-200 line-clamp-2 leading-snug group-hover:text-white">
                      {video.title}
                    </p>
                    <p className="mt-1 text-[11px] text-neutral-500 truncate">
                      {video.channel.name}
                    </p>
                    <p className="text-[10px] text-neutral-600">
                      {video.views.toLocaleString()} views
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
        <div className="min-h-screen bg-black flex items-center justify-center text-xs text-neutral-500">
          Loading player...
        </div>
      }
    >
      <VideoPageContent />
    </Suspense>
  );
}
