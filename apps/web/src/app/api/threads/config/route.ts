import { proxyThreadsRequest } from "@/lib/api/threads-proxy";

export async function GET(): Promise<Response> {
  return proxyThreadsRequest("/config");
}
