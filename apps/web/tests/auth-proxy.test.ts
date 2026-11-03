import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { proxy } from "../src/proxy";
import {
  ACCESS_TOKEN_COOKIE_NAME,
  REFRESH_TOKEN_COOKIE_NAME,
} from "../src/lib/auth/cookies";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("authentication proxy", () => {
  it("refreshes missing access tokens and forwards them to the route", async () => {
    const now = Date.now();
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        access_token: "new-access-token",
        refresh_token: "new-refresh-token",
        token_type: "bearer",
        access_expires_at: new Date(now + 15 * 60000).toISOString(),
        refresh_expires_at: new Date(now + 30 * 86400000).toISOString(),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest("http://localhost/dashboard", {
      headers: { cookie: `${REFRESH_TOKEN_COOKIE_NAME}=current-refresh-token` },
    });

    const response = await proxy(request);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/refresh",
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
    expect(request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)?.value).toBe("new-access-token");
    expect(response.cookies.get(ACCESS_TOKEN_COOKIE_NAME)?.value).toBe("new-access-token");
    expect(response.cookies.get(REFRESH_TOKEN_COOKIE_NAME)?.value).toBe("new-refresh-token");
  });

  it("does not call refresh while an access token cookie is present", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest("http://localhost/dashboard", {
      headers: { cookie: `${ACCESS_TOKEN_COOKIE_NAME}=current-access-token` },
    });

    await proxy(request);

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("clears authentication cookies when refresh returns an invalid payload", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ access_token: "only-one" })));
    const request = new NextRequest("http://localhost/dashboard", {
      headers: { cookie: `${REFRESH_TOKEN_COOKIE_NAME}=current-refresh-token` },
    });

    const response = await proxy(request);

    expect(response.cookies.get(ACCESS_TOKEN_COOKIE_NAME)?.value).toBe("");
    expect(response.cookies.get(REFRESH_TOKEN_COOKIE_NAME)?.value).toBe("");
  });

  it("refreshes when access token is an expired JWT and refresh token is present", async () => {
    const expiredPayload = Buffer.from(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 100 }),
    ).toString("base64url");
    const expiredJwt = `eyJhbGciOiJIUzI1NiJ9.${expiredPayload}.signature`;

    const now = Date.now();
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        access_token: "refreshed-access-token",
        refresh_token: "refreshed-refresh-token",
        token_type: "bearer",
        access_expires_at: new Date(now + 15 * 60000).toISOString(),
        refresh_expires_at: new Date(now + 30 * 86400000).toISOString(),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const request = new NextRequest("http://localhost/dashboard", {
      headers: {
        cookie: `${ACCESS_TOKEN_COOKIE_NAME}=${expiredJwt}; ${REFRESH_TOKEN_COOKIE_NAME}=valid-refresh-token`,
      },
    });

    const response = await proxy(request);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/refresh",
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
    expect(request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)?.value).toBe("refreshed-access-token");
    expect(response.cookies.get(ACCESS_TOKEN_COOKIE_NAME)?.value).toBe("refreshed-access-token");
  });

  it("does not call refresh when access token is an unexpired JWT", async () => {
    const validPayload = Buffer.from(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 600 }),
    ).toString("base64url");
    const validJwt = `eyJhbGciOiJIUzI1NiJ9.${validPayload}.signature`;

    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const request = new NextRequest("http://localhost/dashboard", {
      headers: {
        cookie: `${ACCESS_TOKEN_COOKIE_NAME}=${validJwt}; ${REFRESH_TOKEN_COOKIE_NAME}=valid-refresh-token`,
      },
    });

    await proxy(request);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});

