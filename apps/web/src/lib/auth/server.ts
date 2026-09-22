import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ACCESS_TOKEN_COOKIE_NAME } from "./cookies";
import type { AuthUser } from "./types";

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
  if (!token) {
    return null;
  }

  try {
    const response = await backendRequest("/auth/me", {}, token);
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as AuthUser;
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
