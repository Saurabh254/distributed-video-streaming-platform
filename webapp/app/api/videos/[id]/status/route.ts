import { NextRequest, NextResponse } from "next/server";
import { getSessionAccessToken } from "@/lib/server-auth";

const VIDEO_SERVICE_URL =
  process.env.INTERNAL_VIDEO_SERVICE_URL ||
  process.env.NEXT_PUBLIC_VIDEO_API_URL ||
  "http://localhost:8001";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const auth = await getSessionAccessToken(req);
    if (!auth) {
      return NextResponse.json(
        { detail: "Authentication required" },
        { status: 401 }
      );
    }

    const { id } = await context.params;

    const res = await fetch(`${VIDEO_SERVICE_URL}/api/v1/videos/${id}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${auth.accessToken}`,
      },
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(
        { detail: data.detail || "Failed to fetch video details" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error("Get video status error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to video service" },
      { status: 500 }
    );
  }
}
