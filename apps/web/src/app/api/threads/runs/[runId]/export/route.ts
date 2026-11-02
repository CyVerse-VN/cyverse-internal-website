import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function GET(request: Request, context: RouteContext<"/api/threads/runs/[runId]/export">): Promise<Response> {
  const { runId } = await context.params;
  const format = new URL(request.url).searchParams.get("format") ?? "json";
  if (format !== "json" && format !== "txt") return Response.json({ detail: "Invalid export format" }, { status: 400 });
  return proxyThreadsRequest(`/runs/${encodeURIComponent(runId)}/export?format=${format}`);
}
