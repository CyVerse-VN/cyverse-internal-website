import { proxyResearchRequest } from "@/lib/api/research-proxy";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  return proxyResearchRequest("/tools/research/config");
}
