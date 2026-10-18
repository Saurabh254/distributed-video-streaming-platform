import { NextRequest, NextResponse } from "next/server";

const CATALOG_SERVICE_URL =
  process.env.INTERNAL_CATALOG_SERVICE_URL ||
  process.env.NEXT_PUBLIC_CATALOG_API_URL ||
  "http://localhost:8002";

export async function GET(
  _req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await context.params;
    const targetUrl = `${CATALOG_SERVICE_URL}/api/v1/catalog/videos/${id}`;

    const res = await fetch(targetUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error fetching video detail from catalog service:", error);
    return NextResponse.json(
      { detail: "Failed to fetch video from catalog service" },
      { status: 503 }
    );
  }
}
