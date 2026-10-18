"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  apiGetMe,
  apiLogin,
  apiLogout,
  apiRegister,
  getCachedUser,
  setCachedUser,
} from "./auth-api";
import { AuthUser, LoginPayload, RegisterPayload } from "./auth-types";

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  isAuthModalOpen: boolean;
  authModalMode: "login" | "register";
  openAuthModal: (mode?: "login" | "register") => void;
  closeAuthModal: () => void;
  setAuthModalMode: (mode: "login" | "register") => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<"login" | "register">("login");

  // On mount: check cached user optimistically and validate session via /api/auth/me
  useEffect(() => {
    let mounted = true;

    async function initAuth() {
      const cached = getCachedUser();
      if (cached && mounted) {
        setUser(cached);
      }

      try {
        const freshUser = await apiGetMe();
        if (mounted) {
          setUser(freshUser);
        }
      } catch {
        if (mounted) {
          setUser(null);
          setCachedUser(null);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    initAuth();

    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const loggedInUser = await apiLogin(payload);
    setUser(loggedInUser);
    setIsAuthModalOpen(false);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const registeredUser = await apiRegister(payload);
    setUser(registeredUser);
    setIsAuthModalOpen(false);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  const openAuthModal = useCallback((mode: "login" | "register" = "login") => {
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  }, []);

  const closeAuthModal = useCallback(() => {
    setIsAuthModalOpen(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        isAuthModalOpen,
        authModalMode,
        openAuthModal,
        closeAuthModal,
        setAuthModalMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
