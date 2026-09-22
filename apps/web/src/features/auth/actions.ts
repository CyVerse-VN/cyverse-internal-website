"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import {
  ACCESS_TOKEN_COOKIE_NAME,
  REFRESH_TOKEN_COOKIE_NAME,
  authCookieOptions,
} from "@/lib/auth/cookies";
import { getSafeNextPath } from "@/lib/auth/safe-redirect";
import { backendRequest } from "@/lib/auth/server";
import { isTokenPairResponse, type ActionState } from "@/lib/auth/types";
import { isValidUsername, normalizeUsername } from "@/lib/auth/validation";

export async function loginAction(
  _previousState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const username = normalizeUsername(String(formData.get("username") ?? ""));
  const password = String(formData.get("password") ?? "");
  const nextPath = getSafeNextPath(String(formData.get("next") ?? ""));

  if (!isValidUsername(username)) {
    return { status: "error", message: "Enter a valid username.", username };
  }
  if (password.length < 8 || password.length > 128) {
    return {
      status: "error",
      message: "Password must be between 8 and 128 characters.",
      username,
    };
  }

  let response: Response;
  try {
    response = await backendRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  } catch {
    return {
      status: "error",
      message: "The sign-in service is temporarily unavailable.",
      username,
    };
  }

  if (!response.ok) {
    return { status: "error", message: "Invalid username or password.", username };
  }

  let result: unknown;
  try {
    result = await response.json();
  } catch {
    return { status: "error", message: "The sign-in service returned an invalid response." };
  }
  if (!isTokenPairResponse(result)) {
    return { status: "error", message: "The sign-in service returned an invalid response." };
  }
  const cookieStore = await cookies();
  cookieStore.set(
    ACCESS_TOKEN_COOKIE_NAME,
    result.access_token,
    authCookieOptions(result.access_expires_at),
  );
  cookieStore.set(
    REFRESH_TOKEN_COOKIE_NAME,
    result.refresh_token,
    authCookieOptions(result.refresh_expires_at),
  );
  redirect(nextPath);
}

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(ACCESS_TOKEN_COOKIE_NAME);
  cookieStore.delete(REFRESH_TOKEN_COOKIE_NAME);
  redirect("/login");
}
