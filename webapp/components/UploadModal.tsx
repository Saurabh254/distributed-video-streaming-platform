"use client";

import React, { useState } from "react";
import { X } from "lucide-react";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UploadModal({ isOpen, onClose }: UploadModalProps) {
  const [title, setTitle] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setIsDone(true);
      setTimeout(() => {
        setIsDone(false);
        setTitle("");
        onClose();
      }, 1000);
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        onClick={onClose}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
      />
      <div className="relative w-full max-w-md rounded-lg border border-neutral-800 bg-neutral-950 p-6 shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-neutral-900">
          <h2 className="text-sm font-medium text-neutral-200">Upload Video</h2>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {isDone ? (
          <div className="py-8 text-center text-xs text-neutral-400">
            Uploaded successfully.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-4 text-xs">
            <div className="flex flex-col items-center justify-center rounded border border-dashed border-neutral-800 p-6 text-neutral-500 hover:border-neutral-700 cursor-pointer">
              <span>Select or drop video file</span>
              <span className="mt-1 text-[10px] text-neutral-600">
                MP4, MOV, MKV
              </span>
            </div>

            <div>
              <label className="block text-neutral-400 mb-1">Title</label>
              <input
                type="text"
                placeholder="Video title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded border border-neutral-800 bg-black px-3 py-1.5 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-neutral-400 hover:text-neutral-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!title.trim() || isSubmitting}
                className="rounded bg-neutral-200 px-3.5 py-1.5 text-black font-medium hover:bg-white disabled:opacity-40"
              >
                {isSubmitting ? "Uploading..." : "Publish"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
