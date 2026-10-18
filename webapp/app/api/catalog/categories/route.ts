import { NextResponse } from "next/server";

const CATALOG_SERVICE_URL =
  process.env.INTERNAL_CATALOG_SERVICE_URL ||
  process.env.NEXT_PUBLIC_CATALOG_API_URL ||
  "http://localhost:8002";

export async function GET() {
  try {
    const res = await fetch(`${CATALOG_SERVICE_URL}/api/v1/catalog/categories`, {
      method: "GET",
      headers: { Accept: "application/json" },
      next: { revalidate: 60 },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error fetching categories:", error);
    return NextResponse.json(
      { categories: [] },
      { status: 503 }
    );
  }
}
