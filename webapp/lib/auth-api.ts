import {
  AuthUser,
  LoginPayload,
  MessageResponse,
  RegisterPayload,
} from "./auth-types";

export class AuthError extends Error {
  status?: number;
  details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "AuthError";
    this.status = status;
    this.details = details;
  }
}

const USER_CACHE_KEY = "aurastream_user_cache";

export function getCachedUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const userJson = localStorage.getItem(USER_CACHE_KEY);
  if (!userJson) return null;
  try {
    return JSON.parse(userJson) as AuthUser;
  } catch {
    return null;
  }
}

export function setCachedUser(user: AuthUser | null) {
  if (typeof window === "undefined") return;
  if (user) {
    localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_CACHE_KEY);
  }
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail
        .map((err: { msg?: string }) => err.msg || "Invalid field")
        .join(", ");
    }
    if (data.message) {
      return String(data.message);
    }
  } catch {
    // Non-JSON response
  }
  return response.statusText || "Request failed";
}

/**
 * Register a new user. HttpOnly cookies are set automatically by the server.
 */
export async function apiRegister(payload: RegisterPayload): Promise<AuthUser> {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorMsg = await extractErrorMessage(res);
    throw new AuthError(errorMsg, res.status);
  }

  const data = await res.json();
  const user: AuthUser = data.user;
  setCachedUser(user);
  return user;
}

/**
 * Login with identifier and password. HttpOnly cookies are set automatically by the server.
 */
export async function apiLogin(payload: LoginPayload): Promise<AuthUser> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorMsg = await extractErrorMessage(res);
    throw new AuthError(errorMsg, res.status);
  }

  const data = await res.json();
  const user: AuthUser = data.user;
  setCachedUser(user);
  return user;
}

/**
 * Fetch authenticated user profile using HttpOnly cookie session.
 */
export async function apiGetMe(): Promise<AuthUser> {
  const res = await fetch("/api/auth/me", {
    method: "GET",
  });

  if (!res.ok) {
    setCachedUser(null);
    const errorMsg = await extractErrorMessage(res);
    throw new AuthError(errorMsg, res.status);
  }

  const data = await res.json();
  const user: AuthUser = data.user;
  setCachedUser(user);
  return user;
}

/**
 * Refresh current session via server HttpOnly cookie.
 */
export async function apiRefreshToken(): Promise<void> {
  const res = await fetch("/api/auth/refresh", {
    method: "POST",
  });

  if (!res.ok) {
    setCachedUser(null);
    const errorMsg = await extractErrorMessage(res);
    throw new AuthError(errorMsg, res.status);
  }
}

/**
 * Logout user: invalidates session on server and removes HttpOnly cookies.
 */
export async function apiLogout(): Promise<MessageResponse> {
  try {
    const res = await fetch("/api/auth/logout", {
      method: "POST",
    });
    if (res.ok) {
      setCachedUser(null);
      return await res.json();
    }
  } catch (err) {
    console.warn("Logout request failed:", err);
  } finally {
    setCachedUser(null);
  }

  return { message: "Logged out successfully" };
}
