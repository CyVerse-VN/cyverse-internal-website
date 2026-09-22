import { proxyResearchRequest } from "@/lib/api/research-proxy";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: RouteContext<"/api/research/sessions/[sessionId]">,
): Promise<Response> {
  const { sessionId } = await context.params;
  return proxyResearchRequest(`/tools/research/sessions/${encodeURIComponent(sessionId)}`);
}

export async function PATCH(
  request: Request,
  context: RouteContext<"/api/research/sessions/[sessionId]">,
): Promise<Response> {
  const { sessionId } = await context.params;
  return proxyResearchRequest(`/tools/research/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
  });
}

export async function DELETE(
  _request: Request,
  context: RouteContext<"/api/research/sessions/[sessionId]">,
): Promise<Response> {
  const { sessionId } = await context.params;
  return proxyResearchRequest(`/tools/research/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
}
