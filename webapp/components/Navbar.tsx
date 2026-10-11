"use client";

import React from "react";
import Link from "next/link";
import { Search, Plus } from "lucide-react";

interface NavbarProps {
  onOpenUpload?: () => void;
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
}

export function Navbar({
  onOpenUpload,
  searchQuery = "",
  onSearchChange,
}: NavbarProps) {
  return (
    <header className="sticky top-0 z-30 w-full border-b border-neutral-900 bg-black/90 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <Link
          href="/"
          className="text-sm font-medium tracking-tight text-neutral-100 hover:text-white"
        >
          AuraStream
        </Link>

        {/* Minimal Search */}
        <div className="relative mx-4 flex-1 max-w-xs sm:max-w-sm">
          <div className="relative flex items-center">
            <Search className="absolute left-3 h-3.5 w-3.5 text-neutral-500" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => onSearchChange?.(e.target.value)}
              className="w-full rounded-md border border-neutral-800 bg-neutral-950 py-1.5 pl-8.5 pr-3 text-xs text-neutral-200 placeholder:text-neutral-500 focus:border-neutral-600 focus:outline-none"
            />
          </div>
        </div>

        {/* Right Action */}
        <div className="flex items-center gap-3">
          {onOpenUpload && (
            <button
              onClick={onOpenUpload}
              className="flex items-center gap-1.5 rounded-md border border-neutral-800 bg-neutral-950 px-2.5 py-1 text-xs text-neutral-300 hover:border-neutral-700 hover:text-white transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Upload</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
