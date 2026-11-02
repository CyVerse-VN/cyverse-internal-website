import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function POST(
  request: Request,
  props: { params: Promise<{ accountId: string }> }
): Promise<Response> {
  const params = await props.params;
  const body = await request.text();
  return proxyThreadsRequest(`/accounts/${encodeURIComponent(params.accountId)}/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}
