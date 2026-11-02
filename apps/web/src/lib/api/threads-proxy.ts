import "server-only";

import { backendRequest, getAccessToken } from "@/lib/auth/server";

export async function proxyThreadsRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken();
  if (!token) return Response.json({ detail: "Authentication required" }, { status: 401 });
  try {
    const upstream = await backendRequest(`/tools/threads${path}`, {
      ...init, signal: AbortSignal.timeout(30000),
    }, token);
    const headers = new Headers({
      "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    });
    const disposition = upstream.headers.get("Content-Disposition");
    if (disposition) headers.set("Content-Disposition", disposition);
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch {
    return Response.json({ detail: "The Threads service is temporarily unavailable." }, { status: 503 });
  }
}
