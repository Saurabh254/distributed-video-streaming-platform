import { NextRequest, NextResponse } from "next/server";
import { getSessionAccessToken } from "@/lib/server-auth";

const VIDEO_SERVICE_URL =
  process.env.INTERNAL_VIDEO_SERVICE_URL ||
  process.env.NEXT_PUBLIC_VIDEO_API_URL ||
  "http://localhost:8001";

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const auth = await getSessionAccessToken(req);
    if (!auth) {
      return NextResponse.json(
        { detail: "Authentication required to complete video upload" },
        { status: 401 }
      );
    }

    const { id } = await context.params;
    let body = {};
    try {
      body = await req.json();
    } catch {
      // Body is optional
    }

    const res = await fetch(`${VIDEO_SERVICE_URL}/api/v1/videos/${id}/complete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.accessToken}`,
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(
        { detail: data.detail || "Failed to complete video upload" },
        { status: res.status }
      );
    }

    const response = NextResponse.json(data, { status: 200 });

    if (auth.refreshedTokens) {
      const isProd = process.env.NODE_ENV === "production";
      response.cookies.set("access_token", auth.refreshedTokens.accessToken, {
        httpOnly: true,
        secure: isProd,
        sameSite: "lax",
        path: "/",
        maxAge: auth.refreshedTokens.expiresIn,
      });
      response.cookies.set("refresh_token", auth.refreshedTokens.refreshToken, {
        httpOnly: true,
        secure: isProd,
        sameSite: "lax",
        path: "/",
        maxAge: 7 * 24 * 60 * 60,
      });
    }

    return response;
  } catch (error) {
    console.error("Complete video upload error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to video upload service" },
      { status: 500 }
    );
  }
}
