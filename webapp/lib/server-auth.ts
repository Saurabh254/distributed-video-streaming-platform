import { NextRequest } from "next/server";

const AUTH_SERVICE_URL =
  process.env.INTERNAL_AUTH_SERVICE_URL ||
  process.env.NEXT_PUBLIC_AUTH_API_URL ||
  "http://localhost:8000";

export interface SessionAuthResult {
  accessToken: string;
  refreshedTokens?: {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  };
}

export async function getSessionAccessToken(
  req: NextRequest
): Promise<SessionAuthResult | null> {
  const accessToken = req.cookies.get("access_token")?.value;
  const refreshToken = req.cookies.get("refresh_token")?.value;

  // Case 1: Access token is already present
  if (accessToken) {
    return { accessToken };
  }

  // Case 2: Access token missing or expired, attempt refresh using refresh_token
  if (refreshToken) {
    try {
      const refRes = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (refRes.ok) {
        const refData = await refRes.json();
        return {
          accessToken: refData.access_token,
          refreshedTokens: {
            accessToken: refData.access_token,
            refreshToken: refData.refresh_token,
            expiresIn: refData.expires_in || 15 * 60,
          },
        };
      }
    } catch (err) {
      console.warn("Failed to refresh token in server-auth:", err);
    }
  }

  return null;
}
