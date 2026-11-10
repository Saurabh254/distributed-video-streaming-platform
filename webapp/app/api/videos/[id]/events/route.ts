import { NextRequest, NextResponse } from "next/server";

const VIDEO_SERVICE_URL =
  process.env.INTERNAL_VIDEO_SERVICE_URL ||
  process.env.NEXT_PUBLIC_VIDEO_API_URL ||
  "http://localhost:8001";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await context.params;

    const res = await fetch(`${VIDEO_SERVICE_URL}/api/v1/videos/${id}/events`, {
      method: "GET",
      headers: {
        Accept: "text/event-stream",
      },
    });

    if (!res.ok) {
      const err = await res.text().catch(() => "Failed to connect to SSE stream");
      return new NextResponse(err, { status: res.status });
    }

    return new NextResponse(res.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("SSE stream error:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}
