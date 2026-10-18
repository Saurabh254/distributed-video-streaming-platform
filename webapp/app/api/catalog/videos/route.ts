import { NextRequest, NextResponse } from "next/server";

const CATALOG_SERVICE_URL =
  process.env.INTERNAL_CATALOG_SERVICE_URL ||
  process.env.NEXT_PUBLIC_CATALOG_API_URL ||
  "http://localhost:8002";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const queryString = searchParams.toString();
    const targetUrl = `${CATALOG_SERVICE_URL}/api/v1/catalog/videos${
      queryString ? `?${queryString}` : ""
    }`;

    const res = await fetch(targetUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      next: { revalidate: 15 },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error proxying to catalog service:", error);
    return NextResponse.json(
      {
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
        error: "Catalog service unavailable",
      },
      { status: 503 }
    );
  }
}
