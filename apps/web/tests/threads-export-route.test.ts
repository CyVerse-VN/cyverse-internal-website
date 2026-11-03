import { describe, expect, it, vi } from "vitest";

const { proxy } = vi.hoisted(() => ({ proxy: vi.fn() }));
vi.mock("@/lib/api/threads-proxy", () => ({ proxyThreadsRequest: proxy }));
import { GET } from "../src/app/api/threads/runs/[runId]/export/route";

describe("Threads JSON export route", () => {
  it("forwards the selected detail level and defaults to basic", async () => {
    proxy.mockResolvedValue(new Response("{}"));
    const context = { params: Promise.resolve({ runId: "run-1" }) } as never;
    await GET(new Request("http://localhost/export?format=json&detail=full"), context);
    expect(proxy).toHaveBeenLastCalledWith("/runs/run-1/export?format=json&detail=full");
    await GET(new Request("http://localhost/export"), context);
    expect(proxy).toHaveBeenLastCalledWith("/runs/run-1/export?format=json&detail=basic");
    expect((await GET(new Request("http://localhost/export?detail=invalid"), context)).status).toBe(400);
  });
});
