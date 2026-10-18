"use client";

import React, { useRef, useState } from "react";
import { CheckCircle2, Film, Loader2, Upload, X } from "lucide-react";
import { CATEGORIES } from "@/lib/data";
import {
  completeVideoUpload,
  initiateVideoUpload,
  uploadBinaryToPresignedUrl,
  VideoUploadError,
} from "@/lib/video-api";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess?: () => void;
}

type UploadPhase = "idle" | "initiating" | "uploading" | "completing" | "done";

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
  const [progressPercent, setProgressPercent] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const resetForm = () => {
    setSelectedFile(null);
    setTitle("");
    setDescription("");
    setCategory("Distributed Systems");
    setPhase("idle");
    setProgressPercent(0);
    setErrorMessage(null);
  };

  const handleClose = () => {
    if (phase === "uploading" || phase === "initiating" || phase === "completing") {
      if (!confirm("An upload is currently in progress. Are you sure you want to cancel?")) {
        return;
      }
    }
    resetForm();
    onClose();
  };

  const handleFileChange = (file: File) => {
    setErrorMessage(null);

    // Validate type
    const isAllowed =
      ALLOWED_MIME_TYPES.includes(file.type) ||
      /\.(mp4|mov|mkv|webm)$/i.test(file.name);

    if (!isAllowed) {
      setErrorMessage(
        "Unsupported format. Please select an MP4, MOV, MKV, or WebM video file."
      );
      return;
    }

    // Default title from filename without extension
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
    setProgressPercent(0);

    try {
      // Step 1: Request presigned S3 URL through API Gateway
      const mimeType = selectedFile.type || "video/mp4";
      const initRes = await initiateVideoUpload({
        title: title.trim(),
        description: description.trim() || undefined,
        category,
        filename: selectedFile.name,
        contentType: mimeType,
        fileSize: selectedFile.size,
      });

      // Step 2: Direct upload to S3 / MinIO via presigned PUT URL
      setPhase("uploading");
      await uploadBinaryToPresignedUrl(
        initRes.upload_url,
        selectedFile,
        (percent) => {
          setProgressPercent(percent);
        }
      );

      // Step 3: Complete and confirm upload
      setPhase("completing");
      await completeVideoUpload(initRes.video_id);

      setPhase("done");
      onUploadSuccess?.();

      setTimeout(() => {
        resetForm();
        onClose();
      }, 1800);
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
    phase === "initiating" || phase === "uploading" || phase === "completing";

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
              Upload Video
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

        {/* Success State */}
        {phase === "done" ? (
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
            <CheckCircle2 className="h-10 w-10 text-emerald-400 animate-in zoom-in-50" />
            <p className="text-sm font-medium text-neutral-200">
              Uploaded successfully!
            </p>
            <p className="text-xs text-neutral-500 max-w-xs truncate">
              {title}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-4 text-xs">
            {/* File Dropzone / Picker */}
            {!selectedFile ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center justify-center rounded-lg border border-dashed border-neutral-800 bg-black/40 p-8 text-neutral-400 hover:border-neutral-700 hover:bg-neutral-900/30 cursor-pointer transition-colors"
              >
                <Upload className="h-7 w-7 text-neutral-500 mb-2" />
                <span className="font-medium text-neutral-300">
                  Select or drag video file
                </span>
                <span className="mt-1 text-[11px] text-neutral-500">
                  MP4, MOV, MKV, or WebM (up to 5GB)
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/quicktime,video/webm,video/x-matroska,.mp4,.mov,.mkv,.webm"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileChange(e.target.files[0]);
                    }
                  }}
                />
              </div>
            ) : (
              <div className="flex items-center justify-between rounded-md border border-neutral-800 bg-neutral-900/60 px-3.5 py-2.5">
                <div className="flex items-center gap-3 overflow-hidden">
                  <Film className="h-5 w-5 text-neutral-400 shrink-0" />
                  <div className="overflow-hidden">
                    <p className="text-xs font-medium text-neutral-200 truncate">
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
                {CATEGORIES.filter((c) => c !== "All").map((c) => (
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
                rows={3}
                placeholder="Brief summary of your video..."
                value={description}
                disabled={isWorking}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-md border border-neutral-800 bg-black px-3 py-1.5 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none disabled:opacity-50 resize-none"
              />
            </div>

            {/* Active Upload Progress Bar */}
            {isWorking && (
              <div className="space-y-1.5 pt-1">
                <div className="flex items-center justify-between text-[11px] text-neutral-400">
                  <div className="flex items-center gap-1.5">
                    <Loader2 className="h-3 w-3 animate-spin text-neutral-300" />
                    <span>
                      {phase === "initiating" && "Requesting upload URL..."}
                      {phase === "uploading" && `Uploading to storage: ${progressPercent}%`}
                      {phase === "completing" && "Verifying upload..."}
                    </span>
                  </div>
                  {phase === "uploading" && <span>{progressPercent}%</span>}
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-900">
                  <div
                    className="h-full bg-neutral-200 transition-all duration-200"
                    style={{
                      width: `${
                        phase === "initiating"
                          ? 10
                          : phase === "completing"
                          ? 95
                          : progressPercent
                      }%`,
                    }}
                  />
                </div>
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
                    <span>Processing...</span>
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
