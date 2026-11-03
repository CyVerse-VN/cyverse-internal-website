import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import {
  ACCESS_TOKEN_COOKIE_NAME,
  REFRESH_TOKEN_COOKIE_NAME,
  authCookieOptions,
} from "./cookies";
import { isTokenPairResponse, type AuthUser } from "./types";

function getBackendUrl(): string {
  return (process.env.BACKEND_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
}

export async function backendRequest(
  path: string,
  init: RequestInit = {},
  token?: string,
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(`${getBackendUrl()}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}

export async function getAccessToken(): Promise<string | null> {
  return (await cookies()).get(ACCESS_TOKEN_COOKIE_NAME)?.value ?? null;
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  const token = await getAccessToken();
  if (token) {
    try {
      const response = await backendRequest("/auth/me", {}, token);
      if (response.ok) {
        return (await response.json()) as AuthUser;
      }
    } catch {
      // Continue to refresh fallback if access token validation threw
    }
  }

  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE_NAME)?.value;
  if (!refreshToken) {
    return null;
  }

  try {
    const refreshResponse = await backendRequest("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!refreshResponse.ok) {
      return null;
    }
    const tokens: unknown = await refreshResponse.json();
    if (!isTokenPairResponse(tokens)) {
      return null;
    }

    try {
      cookieStore.set(
        ACCESS_TOKEN_COOKIE_NAME,
        tokens.access_token,
        authCookieOptions(tokens.access_expires_at),
      );
      cookieStore.set(
        REFRESH_TOKEN_COOKIE_NAME,
        tokens.refresh_token,
        authCookieOptions(tokens.refresh_expires_at),
      );
    } catch {
      // In Server Components rendering phase, cookies cannot be directly mutated.
      // The session will be synced on the next proxy request boundary.
    }

    const userResponse = await backendRequest("/auth/me", {}, tokens.access_token);
    if (!userResponse.ok) {
      return null;
    }
    return (await userResponse.json()) as AuthUser;
  } catch {
    return null;
  }
}

export async function requireCurrentUser(nextPath: string): Promise<AuthUser> {
  const user = await getCurrentUser();
  if (!user) {
    redirect(`/login?next=${encodeURIComponent(nextPath)}`);
  }
  return user;
}

export async function requireAdmin(nextPath: string): Promise<AuthUser> {
  const user = await requireCurrentUser(nextPath);
  if (user.role !== "admin") {
    redirect("/dashboard?notice=admin-required");
  }
  return user;
}

export async function readApiError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      return data.detail[0].msg;
    }
  } catch {
    // The fallback below intentionally hides malformed upstream responses.
  }
  return "The request could not be completed.";
}
