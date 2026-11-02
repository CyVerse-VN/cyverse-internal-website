import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function POST(request: Request): Promise<Response> {
  const body = await request.text();
  return proxyThreadsRequest("/sessions/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}
