import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function GET(request: Request): Promise<Response> {
  const search = new URL(request.url).searchParams;
  const params = new URLSearchParams();
  for (const key of ["limit", "offset"]) {
    const value = search.get(key);
    if (value) params.set(key, value);
  }
  return proxyThreadsRequest(`/runs?${params}`);
}

export async function POST(request: Request): Promise<Response> {
  return proxyThreadsRequest("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": request.headers.get("Idempotency-Key") ?? crypto.randomUUID() },
    body: await request.text(),
  });
}
