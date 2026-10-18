import { NextRequest, NextResponse } from "next/server";

const AUTH_SERVICE_URL =
  process.env.INTERNAL_AUTH_SERVICE_URL ||
  process.env.NEXT_PUBLIC_AUTH_API_URL ||
  "http://localhost:8000";

export async function GET(req: NextRequest) {
  let accessToken = req.cookies.get("access_token")?.value;
  const refreshToken = req.cookies.get("refresh_token")?.value;
  const isProd = process.env.NODE_ENV === "production";

  // Case 1: If access_token missing but refresh_token exists, attempt proactive rotation
  if (!accessToken && refreshToken) {
    try {
      const refRes = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (refRes.ok) {
        const refData = await refRes.json();
        accessToken = refData.access_token;

        const meRes = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });

        if (meRes.ok) {
          const user = await meRes.json();
          const response = NextResponse.json({ user });

          response.cookies.set("access_token", refData.access_token, {
            httpOnly: true,
            secure: isProd,
            sameSite: "lax",
            path: "/",
            maxAge: refData.expires_in || 15 * 60,
          });

          response.cookies.set("refresh_token", refData.refresh_token, {
            httpOnly: true,
            secure: isProd,
            sameSite: "lax",
            path: "/",
            maxAge: 7 * 24 * 60 * 60,
          });

          return response;
        }
      }
    } catch (e) {
      console.warn("Proactive refresh failed:", e);
    }
  }

  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  // Case 2: Validate existing access_token against backend /me
  try {
    let meRes = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    // If access token expired, attempt fallback refresh
    if (meRes.status === 401 && refreshToken) {
      const refRes = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (refRes.ok) {
        const refData = await refRes.json();
        meRes = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${refData.access_token}` },
        });

        if (meRes.ok) {
          const user = await meRes.json();
          const response = NextResponse.json({ user });

          response.cookies.set("access_token", refData.access_token, {
            httpOnly: true,
            secure: isProd,
            sameSite: "lax",
            path: "/",
            maxAge: refData.expires_in || 15 * 60,
          });

          response.cookies.set("refresh_token", refData.refresh_token, {
            httpOnly: true,
            secure: isProd,
            sameSite: "lax",
            path: "/",
            maxAge: 7 * 24 * 60 * 60,
          });

          return response;
        }
      }
    }

    if (!meRes.ok) {
      const response = NextResponse.json(
        { detail: "Session expired or invalid" },
        { status: 401 }
      );
      response.cookies.delete("access_token");
      response.cookies.delete("refresh_token");
      return response;
    }

    const user = await meRes.json();
    return NextResponse.json({ user });
  } catch (error) {
    console.error("Me route error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to authentication service" },
      { status: 500 }
    );
  }
}
