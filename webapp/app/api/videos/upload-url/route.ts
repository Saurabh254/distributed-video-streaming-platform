import { NextRequest, NextResponse } from "next/server";
import { getSessionAccessToken } from "@/lib/server-auth";

const VIDEO_SERVICE_URL =
  process.env.INTERNAL_VIDEO_SERVICE_URL ||
  process.env.NEXT_PUBLIC_VIDEO_API_URL ||
  "http://localhost:8001";

export async function POST(req: NextRequest) {
  try {
    const auth = await getSessionAccessToken(req);
    if (!auth) {
      return NextResponse.json(
        { detail: "Authentication required to upload videos" },
        { status: 401 }
      );
    }

    const body = await req.json();
    const payload = {
      title: body.title,
      description: body.description ?? null,
      category: body.category ?? null,
      filename: body.filename,
      content_type: body.contentType || body.content_type,
      file_size: Number(body.fileSize || body.file_size),
    };

    const res = await fetch(`${VIDEO_SERVICE_URL}/api/v1/videos/initiate-upload`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.accessToken}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(
        { detail: data.detail || "Failed to initiate video upload" },
        { status: res.status }
      );
    }

    const response = NextResponse.json(data, { status: 201 });

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
    console.error("Initiate video upload error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to video upload service" },
      { status: 500 }
    );
  }
}
