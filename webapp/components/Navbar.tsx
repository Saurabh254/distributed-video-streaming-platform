"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { LogOut, Plus, Search } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

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
  const { user, isAuthenticated, isLoading, logout, openAuthModal } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close user dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleUploadClick = () => {
    if (!isAuthenticated) {
      openAuthModal("login");
      return;
    }
    onOpenUpload?.();
  };

  const getInitials = (name?: string) => {
    if (!name) return "U";
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <header className="sticky top-0 z-30 w-full border-b border-neutral-900 bg-black/90 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <Link
          href="/"
          className="text-sm font-medium tracking-tight text-neutral-100 hover:text-white transition-colors"
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

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {onOpenUpload && (
            <button
              onClick={handleUploadClick}
              className="flex items-center gap-1.5 rounded-md border border-neutral-800 bg-neutral-950 px-2.5 py-1 text-xs text-neutral-300 hover:border-neutral-700 hover:text-white transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Upload</span>
            </button>
          )}

          {isLoading ? (
            <div className="h-7 w-16 animate-pulse rounded-md bg-neutral-900" />
          ) : isAuthenticated && user ? (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="flex items-center gap-2 rounded-md border border-neutral-800 bg-neutral-950 px-2 py-1 text-xs text-neutral-200 hover:border-neutral-700 hover:text-white transition-colors"
              >
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-neutral-800 text-[10px] font-semibold text-neutral-200">
                  {getInitials(user.username)}
                </div>
                <span className="max-w-[100px] truncate">{user.username}</span>
              </button>

              {/* User Dropdown */}
              {isMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-md border border-neutral-800 bg-neutral-950 p-2 shadow-xl z-50">
                  <div className="px-2 py-1.5 border-b border-neutral-900 mb-1">
                    <p className="text-xs font-medium text-neutral-200 truncate">
                      {user.username}
                    </p>
                    <p className="text-[11px] text-neutral-500 truncate">
                      {user.email}
                    </p>
                  </div>

                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2 rounded px-2 py-1.5 text-xs text-neutral-400 hover:bg-neutral-900 hover:text-red-400 transition-colors"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => openAuthModal("login")}
                className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-1 text-xs text-neutral-300 hover:border-neutral-700 hover:text-white transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => openAuthModal("register")}
                className="hidden sm:inline-flex rounded-md bg-neutral-100 px-3 py-1 text-xs font-medium text-black hover:bg-white transition-colors"
              >
                Sign Up
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
