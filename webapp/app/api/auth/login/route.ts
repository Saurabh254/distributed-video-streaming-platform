import { NextResponse } from "next/server";

const AUTH_SERVICE_URL =
  process.env.INTERNAL_AUTH_SERVICE_URL ||
  process.env.NEXT_PUBLIC_AUTH_API_URL ||
  "http://localhost:8000";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${AUTH_SERVICE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(
        { detail: data.detail || "Authentication failed" },
        { status: res.status }
      );
    }

    const response = NextResponse.json({
      user: data.user,
      message: "Logged in successfully",
    });

    const isProd = process.env.NODE_ENV === "production";

    // Set secure HttpOnly cookies
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
    console.error("Login route error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to authentication service" },
      { status: 500 }
    );
  }
}
