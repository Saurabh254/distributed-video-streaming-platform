"use client";

import React, { useEffect, useState } from "react";
import { AlertCircle, Eye, EyeOff, Loader2, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function AuthModal() {
  const {
    isAuthModalOpen,
    closeAuthModal,
    authModalMode,
    setAuthModalMode,
    login,
    register,
  } = useAuth();

  // Form states
  const [identifier, setIdentifier] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleClose = React.useCallback(() => {
    setErrorMessage(null);
    setPassword("");
    setIdentifier("");
    setUsername("");
    setEmail("");
    closeAuthModal();
  }, [closeAuthModal]);

  // Handle ESC key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isAuthModalOpen) {
        handleClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isAuthModalOpen, handleClose]);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      if (authModalMode === "login") {
        if (!identifier.trim() || !password) {
          setErrorMessage("Please fill in both fields");
          setIsLoading(false);
          return;
        }
        await login({
          identifier: identifier.trim(),
          password,
        });
      } else {
        if (!username.trim() || !email.trim() || !password) {
          setErrorMessage("Please fill in all fields");
          setIsLoading(false);
          return;
        }
        if (password.length < 8) {
          setErrorMessage("Password must be at least 8 characters");
          setIsLoading(false);
          return;
        }
        await register({
          username: username.trim(),
          email: email.trim(),
          password,
        });
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        onClick={handleClose}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
      />

      {/* Modal Card */}
      <div className="relative w-full max-w-sm rounded-lg border border-neutral-800 bg-neutral-950 p-6 shadow-2xl">
        {/* Header & Tabs */}
        <div className="flex items-center justify-between pb-3 border-b border-neutral-900">
          <div className="flex items-center gap-4 text-xs font-medium">
            <button
              type="button"
              onClick={() => {
                setAuthModalMode("login");
                setErrorMessage(null);
              }}
              className={`pb-1 transition-colors ${
                authModalMode === "login"
                  ? "border-b-2 border-white text-white font-semibold"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthModalMode("register");
                setErrorMessage(null);
              }}
              className={`pb-1 transition-colors ${
                authModalMode === "register"
                  ? "border-b-2 border-white text-white font-semibold"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              Create Account
            </button>
          </div>

          <button
            onClick={handleClose}
            className="text-neutral-500 hover:text-neutral-300 transition-colors"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mt-4 flex items-center gap-2 rounded border border-red-950/50 bg-red-950/20 px-3 py-2 text-xs text-red-400">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1 leading-tight">{errorMessage}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5 text-xs">
          {authModalMode === "login" ? (
            /* Login Fields */
            <div>
              <label className="block text-neutral-400 mb-1">
                Username or Email
              </label>
              <input
                type="text"
                autoFocus
                placeholder="alice or alice@example.com"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
                className="w-full rounded border border-neutral-800 bg-black px-3 py-2 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
              />
            </div>
          ) : (
            /* Register Fields */
            <>
              <div>
                <label className="block text-neutral-400 mb-1">Username</label>
                <input
                  type="text"
                  autoFocus
                  placeholder="alice"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  pattern="^[a-zA-Z0-9_-]+$"
                  title="Username must contain only letters, numbers, underscores, or hyphens"
                  required
                  className="w-full rounded border border-neutral-800 bg-black px-3 py-2 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-neutral-400 mb-1">Email</label>
                <input
                  type="email"
                  placeholder="alice@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full rounded border border-neutral-800 bg-black px-3 py-2 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-neutral-400 mb-1">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder={
                  authModalMode === "register"
                    ? "Minimum 8 characters"
                    : "Your password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded border border-neutral-800 bg-black px-3 py-2 pr-9 text-neutral-200 placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-3.5 w-3.5" />
                ) : (
                  <Eye className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 rounded bg-neutral-200 px-4 py-2 text-xs font-medium text-black hover:bg-white disabled:opacity-40 transition-colors"
            >
              {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              <span>
                {isLoading
                  ? authModalMode === "login"
                    ? "Signing in..."
                    : "Creating account..."
                  : authModalMode === "login"
                  ? "Sign In"
                  : "Create Account"}
              </span>
            </button>
          </div>

          <div className="pt-2 text-center text-[11px] text-neutral-500">
            {authModalMode === "login" ? (
              <span>
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setAuthModalMode("register");
                    setErrorMessage(null);
                  }}
                  className="text-neutral-300 hover:underline underline-offset-2"
                >
                  Create one
                </button>
              </span>
            ) : (
              <span>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setAuthModalMode("login");
                    setErrorMessage(null);
                  }}
                  className="text-neutral-300 hover:underline underline-offset-2"
                >
                  Sign in
                </button>
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
