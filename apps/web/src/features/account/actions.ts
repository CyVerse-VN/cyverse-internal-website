"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import {
  ACCESS_TOKEN_COOKIE_NAME,
  REFRESH_TOKEN_COOKIE_NAME,
  authCookieOptions,
} from "@/lib/auth/cookies";
import { backendRequest, getAccessToken, readApiError } from "@/lib/auth/server";
import {
  isAuthUser,
  isTokenPairResponse,
  type ActionState,
} from "@/lib/auth/types";

async function authenticatedToken(): Promise<string | null> {
  return getAccessToken();
}

export async function updateProfileAction(
  _previousState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const displayName = String(formData.get("display_name") ?? "").trim();
  const team = String(formData.get("team") ?? "").trim();
  if (!displayName || displayName.length > 100) {
    return { status: "error", message: "Display name must be between 1 and 100 characters." };
  }
  if (team.length > 100) {
    return { status: "error", message: "Team must be 100 characters or fewer." };
  }

  const token = await authenticatedToken();
  if (!token) {
    return { status: "error", message: "Your session has expired. Please sign in again." };
  }

  let response: Response;
  try {
    response = await backendRequest(
      "/auth/me",
      {
        method: "PATCH",
        body: JSON.stringify({ display_name: displayName, team: team || null }),
      },
      token,
    );
  } catch {
    return { status: "error", message: "Account settings are temporarily unavailable." };
  }
  if (!response.ok) {
    return { status: "error", message: await readApiError(response) };
  }

  const user: unknown = await response.json().catch(() => null);
  if (!isAuthUser(user)) {
    return { status: "error", message: "The account service returned an invalid response." };
  }
  revalidatePath("/(dashboard)", "layout");
  return { status: "success", message: "Profile details updated." };
}

export async function changePasswordAction(
  _previousState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const currentPassword = String(formData.get("current_password") ?? "");
  const newPassword = String(formData.get("new_password") ?? "");
  const confirmPassword = String(formData.get("confirm_password") ?? "");
  if (currentPassword.length < 8 || currentPassword.length > 128) {
    return { status: "error", message: "Enter your current password." };
  }
  if (newPassword.length < 8 || newPassword.length > 128) {
    return { status: "error", message: "New password must be between 8 and 128 characters." };
  }
  if (newPassword !== confirmPassword) {
    return { status: "error", message: "New password confirmation does not match." };
  }
  if (currentPassword === newPassword) {
    return { status: "error", message: "New password must be different from the current password." };
  }

  const token = await authenticatedToken();
  if (!token) {
    return { status: "error", message: "Your session has expired. Please sign in again." };
  }

  let response: Response;
  try {
    response = await backendRequest(
      "/auth/me/change-password",
      {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      },
      token,
    );
  } catch {
    return { status: "error", message: "Account settings are temporarily unavailable." };
  }
  if (!response.ok) {
    return { status: "error", message: await readApiError(response) };
  }

  const tokens: unknown = await response.json().catch(() => null);
  if (!isTokenPairResponse(tokens)) {
    return { status: "error", message: "The account service returned an invalid response." };
  }
  const cookieStore = await cookies();
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
  return {
    status: "success",
    message: "Password updated. Other signed-in sessions have been invalidated.",
  };
}
