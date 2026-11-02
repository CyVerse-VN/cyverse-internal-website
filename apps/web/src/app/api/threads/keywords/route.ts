import { NextRequest } from "next/server";
import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function POST(request: NextRequest): Promise<Response> {
  const body = await request.text();
  return proxyThreadsRequest("/keywords", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}
