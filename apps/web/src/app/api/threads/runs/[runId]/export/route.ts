import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function GET(request: Request, context: RouteContext<"/api/threads/runs/[runId]/export">): Promise<Response> {
  const { runId } = await context.params;
  const params = new URL(request.url).searchParams;
  const format = params.get("format") ?? "json";
  const detail = params.get("detail") ?? "basic";
  if (format !== "json" && format !== "txt") return Response.json({ detail: "Invalid export format" }, { status: 400 });
  if (!["basic", "standard", "full"].includes(detail)) return Response.json({ detail: "Invalid JSON detail level" }, { status: 400 });
  return proxyThreadsRequest(`/runs/${encodeURIComponent(runId)}/export?format=${format}&detail=${detail}`);
}
