import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function GET(_request: Request, context: RouteContext<"/api/threads/runs/[runId]">): Promise<Response> {
  const { runId } = await context.params;
  return proxyThreadsRequest(`/runs/${encodeURIComponent(runId)}`);
}

export async function PATCH(request: Request, context: RouteContext<"/api/threads/runs/[runId]">): Promise<Response> {
  const { runId } = await context.params;
  return proxyThreadsRequest(`/runs/${encodeURIComponent(runId)}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: await request.text(),
  });
}

export async function DELETE(_request: Request, context: RouteContext<"/api/threads/runs/[runId]">): Promise<Response> {
  const { runId } = await context.params;
  return proxyThreadsRequest(`/runs/${encodeURIComponent(runId)}`, { method: "DELETE" });
}
