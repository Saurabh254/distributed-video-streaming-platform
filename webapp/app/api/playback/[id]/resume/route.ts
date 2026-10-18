import { NextRequest, NextResponse } from "next/server";
import { getSessionAccessToken } from "@/lib/server-auth";

const PLAYBACK_SERVICE_URL =
  process.env.INTERNAL_PLAYBACK_SERVICE_URL ||
  process.env.NEXT_PUBLIC_PLAYBACK_API_URL ||
  "http://localhost:8003";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await context.params;
    const auth = await getSessionAccessToken(req);

    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (auth?.accessToken) {
      headers.Authorization = `Bearer ${auth.accessToken}`;
    }

    const targetUrl = `${PLAYBACK_SERVICE_URL}/api/v1/playback/${id}/resume`;
    const res = await fetch(targetUrl, {
      method: "GET",
      headers,
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error fetching resume position:", error);
    return NextResponse.json(
      { video_id: "", resume_position_seconds: 0.0, completed: false },
      { status: 200 }
    );
  }
}
