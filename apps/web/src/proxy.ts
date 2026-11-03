import { type NextRequest, NextResponse } from "next/server";

import {
  ACCESS_TOKEN_COOKIE_NAME,
  REFRESH_TOKEN_COOKIE_NAME,
  authCookieOptions,
} from "./lib/auth/cookies";
import { isTokenPairResponse } from "./lib/auth/types";

function getBackendUrl(): string {
  return (process.env.BACKEND_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
}

function clearAuthCookies(response: NextResponse): NextResponse {
  response.cookies.delete(ACCESS_TOKEN_COOKIE_NAME);
  response.cookies.delete(REFRESH_TOKEN_COOKIE_NAME);
  return response;
}

function decodeJwtPayload(token: string): { exp?: unknown } | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const jsonStr =
      typeof Buffer !== "undefined"
        ? Buffer.from(base64, "base64").toString("utf-8")
        : atob(base64);
    return JSON.parse(jsonStr) as { exp?: unknown };
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string | undefined | null): boolean {
  if (!token) {
    return true;
  }
  const payload = decodeJwtPayload(token);
  if (payload && typeof payload.exp === "number") {
    return payload.exp * 1000 <= Date.now() + 30_000;
  }
  return false;
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)?.value;
  if (accessToken && !isTokenExpired(accessToken)) {
    return NextResponse.next();
  }

  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)?.value;
  if (!refreshToken) {
    return NextResponse.next();
  }

  try {
    const refreshResponse = await fetch(`${getBackendUrl()}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!refreshResponse.ok) {
      return clearAuthCookies(NextResponse.next());
    }

    const tokens: unknown = await refreshResponse.json();
    if (!isTokenPairResponse(tokens)) {
      return clearAuthCookies(NextResponse.next());
    }
    request.cookies.set(ACCESS_TOKEN_COOKIE_NAME, tokens.access_token);
    request.cookies.set(REFRESH_TOKEN_COOKIE_NAME, tokens.refresh_token);

    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("cookie", request.cookies.toString());
    const response = NextResponse.next({ request: { headers: requestHeaders } });
    response.cookies.set(
      ACCESS_TOKEN_COOKIE_NAME,
      tokens.access_token,
      authCookieOptions(tokens.access_expires_at),
    );
    response.cookies.set(
      REFRESH_TOKEN_COOKIE_NAME,
      tokens.refresh_token,
      authCookieOptions(tokens.refresh_expires_at),
    );
    return response;
  } catch {
    return clearAuthCookies(NextResponse.next());
  }
}

export const config = {
  matcher: [
    "/",
    "/login",
    "/dashboard/:path*",
    "/admin/:path*",
    "/runs/:path*",
    "/schedules/:path*",
    "/settings/:path*",
    "/tools/:path*",
    "/api/research/:path*",
    "/api/threads/:path*",
  ],
};
