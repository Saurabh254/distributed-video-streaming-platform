import { NextRequest, NextResponse } from "next/server";
import { getSessionAccessToken } from "@/lib/server-auth";

const PLAYBACK_SERVICE_URL =
  process.env.INTERNAL_PLAYBACK_SERVICE_URL ||
  process.env.NEXT_PUBLIC_PLAYBACK_API_URL ||
  "http://localhost:8003";

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await context.params;
    const body = await req.json();
    const auth = await getSessionAccessToken(req);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (auth?.accessToken) {
      headers.Authorization = `Bearer ${auth.accessToken}`;
    }

    const targetUrl = `${PLAYBACK_SERVICE_URL}/api/v1/playback/${id}/heartbeat`;
    const res = await fetch(targetUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error reporting playback heartbeat:", error);
    return NextResponse.json(
      { status: "error", detail: "Playback service unavailable" },
      { status: 503 }
    );
  }
}
