import { afterEach, describe, expect, it, vi } from "vitest";

const { getAccessToken, backendRequest } = vi.hoisted(() => ({ getAccessToken: vi.fn(), backendRequest: vi.fn() }));
vi.mock("server-only", () => ({}));
vi.mock("@/lib/auth/server", () => ({ getAccessToken, backendRequest }));
import { proxyThreadsRequest } from "../src/lib/api/threads-proxy";

afterEach(() => vi.resetAllMocks());

describe("Threads proxy", () => {
  it("rejects anonymous requests before contacting the backend", async () => {
    getAccessToken.mockResolvedValue(null);
    expect((await proxyThreadsRequest("/runs")).status).toBe(401);
    expect(backendRequest).not.toHaveBeenCalled();
  });

  it("forwards server credentials and preserves download headers", async () => {
    getAccessToken.mockResolvedValue("fixture-token");
    backendRequest.mockResolvedValue(new Response("fixture report", { headers: {
      "Content-Type": "text/plain", "Content-Disposition": 'attachment; filename="threads.txt"',
    } }));
    const response = await proxyThreadsRequest("/runs/fixture/export?format=txt");
    expect(backendRequest).toHaveBeenCalledWith("/tools/threads/runs/fixture/export?format=txt", expect.any(Object), "fixture-token");
    expect(await response.text()).toBe("fixture report");
    expect(response.headers.get("Content-Disposition")).toContain("attachment");
    expect(response.headers.get("Cache-Control")).toContain("no-store");
  });

  it("hides raw upstream failures", async () => {
    getAccessToken.mockResolvedValue("fixture-token");
    backendRequest.mockRejectedValue(new Error("sensitive upstream details"));
    const response = await proxyThreadsRequest("/config");
    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain("sensitive");
  });
});
