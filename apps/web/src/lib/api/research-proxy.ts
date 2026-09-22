import "server-only";

import { backendRequest, getAccessToken } from "@/lib/auth/server";

export async function proxyResearchRequest(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await getAccessToken();
  if (!token) {
    return Response.json({ detail: "Authentication required" }, { status: 401 });
  }
  try {
    const upstream = await backendRequest(path, init, token);
    if (upstream.status === 204) {
      return new Response(null, {
        status: 204,
        headers: { "Cache-Control": "no-store" },
      });
    }
    const body = await upstream.arrayBuffer();
    return new Response(body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { detail: "The research service is temporarily unavailable." },
      { status: 503 },
    );
  }
}
