import { proxyResearchRequest } from "@/lib/api/research-proxy";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const query = new URLSearchParams();
  if (url.searchParams.get("cursor")) query.set("cursor", url.searchParams.get("cursor")!);
  if (url.searchParams.get("limit")) query.set("limit", url.searchParams.get("limit")!);
  const suffix = query.size ? `?${query}` : "";
  return proxyResearchRequest(`/tools/research/sessions${suffix}`);
}

export async function POST(request: Request): Promise<Response> {
  return proxyResearchRequest("/tools/research/sessions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": request.headers.get("Idempotency-Key") ?? crypto.randomUUID(),
    },
    body: await request.text(),
  });
}
