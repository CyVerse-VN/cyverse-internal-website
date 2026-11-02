import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function POST(_request: Request, context: RouteContext<"/api/threads/runs/[runId]/cancel">): Promise<Response> {
  const { runId } = await context.params;
  return proxyThreadsRequest(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
}
