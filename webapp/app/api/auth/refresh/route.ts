import { NextRequest, NextResponse } from "next/server";

const AUTH_SERVICE_URL =
  process.env.INTERNAL_AUTH_SERVICE_URL ||
  process.env.NEXT_PUBLIC_AUTH_API_URL ||
  "http://localhost:8000";

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get("refresh_token")?.value;
  if (!refreshToken) {
    return NextResponse.json(
      { detail: "No refresh token available" },
      { status: 401 }
    );
  }

  try {
    const res = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = await res.json();
    if (!res.ok) {
      const response = NextResponse.json(
        { detail: data.detail || "Refresh failed" },
        { status: res.status }
      );
      response.cookies.delete("access_token");
      response.cookies.delete("refresh_token");
      return response;
    }

    const response = NextResponse.json({
      message: "Tokens refreshed successfully",
    });

    const isProd = process.env.NODE_ENV === "production";

    response.cookies.set("access_token", data.access_token, {
      httpOnly: true,
      secure: isProd,
      sameSite: "lax",
      path: "/",
      maxAge: data.expires_in || 15 * 60,
    });

    response.cookies.set("refresh_token", data.refresh_token, {
      httpOnly: true,
      secure: isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60,
    });

    return response;
  } catch (error) {
    console.error("Refresh route error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to authentication service" },
      { status: 500 }
    );
  }
}
