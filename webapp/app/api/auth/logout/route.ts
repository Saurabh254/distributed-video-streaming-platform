import { NextRequest, NextResponse } from "next/server";

const AUTH_SERVICE_URL =
  process.env.INTERNAL_AUTH_SERVICE_URL ||
  process.env.NEXT_PUBLIC_AUTH_API_URL ||
  "http://localhost:8000";

export async function POST(req: NextRequest) {
  const accessToken = req.cookies.get("access_token")?.value;
  const refreshToken = req.cookies.get("refresh_token")?.value;

  if (accessToken || refreshToken) {
    try {
      await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (e) {
      console.warn("Backend logout error (safe to ignore on client):", e);
    }
  }

  const response = NextResponse.json({
    message: "Logged out successfully",
  });

  // Clear both cookies
  response.cookies.delete("access_token");
  response.cookies.delete("refresh_token");

  return response;
}
