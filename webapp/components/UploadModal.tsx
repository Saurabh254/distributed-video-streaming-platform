"use client";

import React, { useRef, useState } from "react";
import { CheckCircle2, Film, Loader2, Play, Sparkles, Upload, X } from "lucide-react";
import Link from "next/link";
import {
  completeVideoUpload,
  initiateVideoUpload,
  uploadBinaryToPresignedUrl,
  VideoUploadError,
} from "@/lib/video-api";

const UPLOAD_CATEGORIES = [
  "General",
  "Distributed Systems",
  "Transcoding & AV1",
  "Edge Architecture",
  "Low Latency HLS",
  "Cloud Infrastructure",
  "Cinema & 4K",
  "Live Events",
];

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess?: () => void;
}

type UploadPhase =
  | "idle"
  | "initiating"
  | "uploading"
  | "completing"
  | "processing"
  | "published"
  | "error";

const ALLOWED_MIME_TYPES = [
  "video/mp4",
  "video/quicktime",
  "video/webm",
  "video/x-matroska",
];

function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export function UploadModal({ isOpen, onClose, onUploadSuccess }: UploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Distributed Systems");
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [uploadPercent, setUploadPercent] = useState(0);
  const [processingPercent, setProcessingPercent] = useState(0);
  const [stepDescription, setStepDescription] = useState("");
  const [publishedVideoId, setPublishedVideoId] = useState<string | null>(null);
  const [publishedData, setPublishedData] = useState<{
    thumbnail_url?: string;
    hls_master_playlist_url?: string;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  if (!isOpen) return null;

  const resetForm = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setSelectedFile(null);
    setTitle("");
    setDescription("");
    setCategory("Distributed Systems");
    setPhase("idle");
    setUploadPercent(0);
    setProcessingPercent(0);
    setStepDescription("");
    setPublishedVideoId(null);
    setPublishedData(null);
    setErrorMessage(null);
  };

  const handleClose = () => {
    if (
      phase === "uploading" ||
      phase === "initiating" ||
      phase === "completing" ||
      phase === "processing"
    ) {
      if (!confirm("An upload/processing pipeline is active. Are you sure you want to exit?")) {
        return;
      }
    }
    resetForm();
    onClose();
  };

  const handleFileChange = (file: File) => {
    setErrorMessage(null);

    const isAllowed =
      ALLOWED_MIME_TYPES.includes(file.type) ||
      /\.(mp4|mov|mkv|webm)$/i.test(file.name);

    if (!isAllowed) {
      setErrorMessage(
        "Unsupported format. Please select an MP4, MOV, MKV, or WebM video file."
      );
      return;
    }

    const baseName = file.name.replace(/\.[^/.]+$/, "");
    if (!title.trim()) {
      setTitle(baseName.replace(/[_-]/g, " "));
    }

    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (phase !== "idle") return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !title.trim() || phase !== "idle") return;

    setErrorMessage(null);
    setPhase("initiating");
    setUploadPercent(0);
    setProcessingPercent(0);

    try {
      // Step 1: Request presigned S3 upload URL
      const mimeType = selectedFile.type || "video/mp4";
      const initRes = await initiateVideoUpload({
        title: title.trim(),
        description: description.trim() || undefined,
        category,
        filename: selectedFile.name,
        contentType: mimeType,
        fileSize: selectedFile.size,
      });

      const videoId = initRes.video_id;
      setPublishedVideoId(videoId);

      // Step 2: Direct upload to S3 via presigned PUT URL
      setPhase("uploading");
      await uploadBinaryToPresignedUrl(
        initRes.upload_url,
        selectedFile,
        (percent) => {
          setUploadPercent(percent);
        }
      );

      // Step 3: Complete and confirm upload
      setPhase("completing");
      await completeVideoUpload(videoId);

      // Step 4: Subscribe to Server-Sent Events (SSE) for processing progression
      setPhase("processing");
      setStepDescription("Initializing media pipeline...");

      const eventSource = new EventSource(`/api/videos/${videoId}/events`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.step) {
            setStepDescription(data.step);
          }
          if (typeof data.progress === "number") {
            setProcessingPercent(Math.round(data.progress));
          }

          const isTerminalSuccess =
            data.status === "ready" ||
            data.status === "completed" ||
            data.event_type === "video.vod.completed";

          const isTerminalFailed =
            data.status === "failed" ||
            data.event_type === "video.vod.failed";

          if (isTerminalSuccess) {
            setProcessingPercent(100);
            setPublishedData(data.data || {});
            setPhase("published");
            eventSource.close();
            onUploadSuccess?.();
          } else if (isTerminalFailed) {
            setErrorMessage(data.error || "Video processing encountered an error.");
            setPhase("error");
            eventSource.close();
          }
        } catch {
          // Keep-alive comments or raw pings
        }
      };

      eventSource.onerror = (err) => {
        console.warn("SSE connection status check:", err);
      };
    } catch (err: unknown) {
      console.error("Upload error:", err);
      setPhase("idle");
      if (err instanceof VideoUploadError) {
        setErrorMessage(err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred during upload.");
      }
    }
  };

  const isWorking =
    phase === "initiating" ||
    phase === "uploading" ||
    phase === "completing" ||
    phase === "processing";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        onClick={handleClose}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-lg rounded-xl border border-neutral-800 bg-neutral-950 p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-neutral-900">
          <div className="flex items-center gap-2">
            <Film className="h-4 w-4 text-neutral-400" />
            <h2 className="text-sm font-semibold text-neutral-200">
              {phase === "published" ? "Video Published" : "Upload Video"}
            </h2>
          </div>
          <button
            onClick={handleClose}
            disabled={isWorking}
            className="text-neutral-500 hover:text-neutral-300 disabled:opacity-30"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mt-3 rounded-md bg-red-950/60 border border-red-900/60 p-2.5 text-xs text-red-200">
            {errorMessage}
          </div>
        )}

        {/* Published Success Screen */}
        {phase === "published" ? (
          <div className="py-6 text-center space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-950/80 border border-emerald-800/80">
              <CheckCircle2 className="h-7 w-7 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-neutral-100">
                Published & Ready to Stream!
              </h3>
              <p className="mt-1 text-xs text-neutral-400">
                &ldquo;{title}&rdquo; is processed into adaptive bitrate HLS with multi-resolution thumbnails.
              </p>
            </div>

            {/* Thumbnail preview if available */}
            {publishedData?.thumbnail_url && (
              <div className="relative mx-auto h-32 w-56 overflow-hidden rounded-lg border border-neutral-800 bg-neutral-900">
                <img
                  src={publishedData.thumbnail_url}
                  alt="Thumbnail"
                  className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                  <Play className="h-6 w-6 text-white/90 drop-shadow" />
                </div>
              </div>
            )}

            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={() => {
                  resetForm();
                  onClose();
                }}
                className="rounded-md border border-neutral-800 bg-neutral-900 px-4 py-2 text-xs font-medium text-neutral-300 hover:bg-neutral-800"
              >
                Close
              </button>
              {publishedVideoId && (
                <Link
                  href={`/video?id=${publishedVideoId}`}
                  onClick={() => {
                    resetForm();
                    onClose();
                  }}
                  className="flex items-center gap-1.5 rounded-md bg-emerald-500 px-4 py-2 text-xs font-medium text-black hover:bg-emerald-400 transition-colors"
                >
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Watch Video</span>
                </Link>
              )}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-3.5 text-xs">
            {/* File Dropzone */}
            {!selectedFile ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center justify-center rounded-lg border border-dashed border-neutral-800 bg-neutral-900/30 p-6 text-center cursor-pointer hover:border-neutral-700 hover:bg-neutral-900/50 transition-colors"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-900 border border-neutral-800 mb-2">
                  <Upload className="h-4 w-4 text-neutral-400" />
                </div>
                <p className="text-neutral-300 font-medium text-xs">
                  Click to browse or drag and drop video
                </p>
                <p className="text-[11px] text-neutral-500 mt-1">
                  MP4, MOV, WebM, or MKV (up to 5GB)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*,.mkv"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileChange(e.target.files[0]);
                    }
                  }}
                />
              </div>
            ) : (
              <div className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <Film className="h-4 w-4 text-neutral-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-neutral-200 font-medium truncate">
                      {selectedFile.name}
                    </p>
                    <p className="text-[11px] text-neutral-500">
                      {formatBytes(selectedFile.size)}
                    </p>
                  </div>
                </div>
                {!isWorking && (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    className="text-xs text-neutral-400 hover:text-neutral-200 underline shrink-0 ml-2"
                  >
                    Change
                  </button>
                )}
              </div>
            )}

            {/* Title */}
            <div>
              <label className="block text-neutral-400 mb-1">
                Title <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                placeholder="Video title"
                value={title}
                disabled={isWorking}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-md border border-neutral-800 bg-black px-3 py-1.5 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none disabled:opacity-50"
              />
            </div>

            {/* Category Dropdown */}
            <div>
              <label className="block text-neutral-400 mb-1">Category</label>
              <select
                value={category}
                disabled={isWorking}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-md border border-neutral-800 bg-black px-3 py-1.5 text-neutral-200 focus:border-neutral-600 focus:outline-none disabled:opacity-50"
              >
                {UPLOAD_CATEGORIES.map((c) => (
                  <option key={c} value={c} className="bg-neutral-950 text-neutral-200">
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Description */}
            <div>
              <label className="block text-neutral-400 mb-1">
                Description (optional)
              </label>
              <textarea
                rows={2}
                placeholder="Brief summary of your video..."
                value={description}
                disabled={isWorking}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-md border border-neutral-800 bg-black px-3 py-1.5 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none disabled:opacity-50 resize-none"
              />
            </div>

            {/* Active Progress Bar & Live Status */}
            {isWorking && (
              <div className="space-y-2 pt-1 rounded-lg border border-neutral-800/80 bg-neutral-900/50 p-3">
                <div className="flex items-center justify-between text-[11px] text-neutral-300">
                  <div className="flex items-center gap-1.5">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-400" />
                    <span className="font-medium text-neutral-200">
                      {phase === "initiating" && "Requesting upload credentials..."}
                      {phase === "uploading" && `Uploading binary to storage (${uploadPercent}%)`}
                      {phase === "completing" && "Verifying upload completion..."}
                      {phase === "processing" && (stepDescription || "Processing video...")}
                    </span>
                  </div>
                  <span className="font-mono text-neutral-400">
                    {phase === "uploading" && `${uploadPercent}%`}
                    {phase === "processing" && `${processingPercent}%`}
                  </span>
                </div>

                <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-900 border border-neutral-800">
                  <div
                    className={`h-full transition-all duration-300 ${
                      phase === "processing"
                        ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                        : "bg-neutral-200"
                    }`}
                    style={{
                      width: `${
                        phase === "initiating"
                          ? 10
                          : phase === "uploading"
                          ? uploadPercent
                          : phase === "completing"
                          ? 98
                          : Math.max(5, processingPercent)
                      }%`,
                    }}
                  />
                </div>

                {phase === "processing" && (
                  <div className="flex items-center justify-between text-[10px] text-neutral-500 pt-0.5">
                    <span className="flex items-center gap-1 text-emerald-400/90">
                      <Sparkles className="h-3 w-3" />
                      Live pipeline event streaming via SSE
                    </span>
                    <span>Status: Processing</span>
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2 border-t border-neutral-900">
              <button
                type="button"
                onClick={handleClose}
                disabled={isWorking}
                className="rounded px-3 py-1.5 text-neutral-400 hover:text-neutral-200 disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!selectedFile || !title.trim() || isWorking}
                className="flex items-center gap-1.5 rounded bg-neutral-100 px-4 py-1.5 text-black font-medium hover:bg-white disabled:opacity-40 transition-colors"
              >
                {isWorking ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>
                      {phase === "uploading" ? "Uploading..." : "Processing..."}
                    </span>
                  </>
                ) : (
                  <span>Publish</span>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
