import { proxyResearchRequest } from "@/lib/api/research-proxy";

export const dynamic = "force-dynamic";

export async function POST(
  _request: Request,
  context: RouteContext<"/api/research/sessions/[sessionId]/cancel">,
): Promise<Response> {
  const { sessionId } = await context.params;
  return proxyResearchRequest(
    `/tools/research/sessions/${encodeURIComponent(sessionId)}/cancel`,
    { method: "POST" },
  );
}
