"use server";

import { revalidatePath } from "next/cache";

import {
  backendRequest,
  getAccessToken,
  readApiError,
  requireAdmin,
} from "@/lib/auth/server";
import type { ActionState } from "@/lib/auth/types";
import { isValidUsername, normalizeUsername } from "@/lib/auth/validation";

async function getAdminToken(): Promise<string> {
  await requireAdmin("/admin/users");
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Access token is missing");
  }
  return token;
}

function passwordError(password: string): ActionState | null {
  if (password.length < 8 || password.length > 128) {
    return { status: "error", message: "Password must be between 8 and 128 characters." };
  }
  return null;
}

export async function createUserAction(
  _previousState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const username = normalizeUsername(String(formData.get("username") ?? ""));
  const password = String(formData.get("password") ?? "");
  const displayName = String(formData.get("display_name") ?? "").trim();
  const team = String(formData.get("team") ?? "").trim();
  const role = formData.get("role") === "admin" ? "admin" : "member";

  if (!isValidUsername(username)) {
    return { status: "error", message: "Username must be 3–64 characters with no spaces, using only letters, numbers, dots, underscores, or hyphens." };
  }
  if (!displayName) {
    return { status: "error", message: "Display name is required." };
  }
  const invalidPassword = passwordError(password);
  if (invalidPassword) {
    return invalidPassword;
  }

  const token = await getAdminToken();
  let response: Response;
  try {
    response = await backendRequest(
      "/admin/users",
      {
        method: "POST",
        body: JSON.stringify({
          username,
          password,
          display_name: displayName,
          team: team || null,
          role,
        }),
      },
      token,
    );
  } catch {
    return { status: "error", message: "The user service is temporarily unavailable." };
  }
  if (!response.ok) {
    return { status: "error", message: await readApiError(response) };
  }
  revalidatePath("/admin/users");
  return { status: "success", message: `Created ${username}.` };
}

export async function updateUserAction(
  _previousState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const userId = String(formData.get("user_id") ?? "");
  const displayName = String(formData.get("display_name") ?? "").trim();
  const team = String(formData.get("team") ?? "").trim();
  const role = formData.get("role") === "admin" ? "admin" : "member";
  if (!userId || !displayName) {
    return { status: "error", message: "Display name is required." };
  }

  const token = await getAdminToken();
  let response: Response;
  try {
    response = await backendRequest(
      `/admin/users/${encodeURIComponent(userId)}`,
      {
        method: "PATCH",
        body: JSON.stringify({ display_name: displayName, team: team || null, role }),
      },
      token,
    );
  } catch {
    return { status: "error", message: "The user service is temporarily unavailable." };
  }
  if (!response.ok) {
    return { status: "error", message: await readApiError(response) };
  }
  revalidatePath("/admin/users");
  return { status: "success", message: "User details updated." };
}

export async function toggleUserStatusAction(
  _previousState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const userId = String(formData.get("user_id") ?? "");
  const isActive = formData.get("is_active") === "true";
  const token = await getAdminToken();
  let response: Response;
  try {
    response = await backendRequest(
      `/admin/users/${encodeURIComponent(userId)}`,
      { method: "PATCH", body: JSON.stringify({ is_active: isActive }) },
      token,
    );
  } catch {
    return { status: "error", message: "The user service is temporarily unavailable." };
  }
  if (!response.ok) {
    return { status: "error", message: await readApiError(response) };
  }
  revalidatePath("/admin/users");
  return { status: "success", message: isActive ? "User activated." : "User deactivated." };
}

export async function resetPasswordAction(
  _previousState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const userId = String(formData.get("user_id") ?? "");
  const password = String(formData.get("password") ?? "");
  const invalidPassword = passwordError(password);
  if (invalidPassword) {
    return invalidPassword;
  }

  const token = await getAdminToken();
  let response: Response;
  try {
    response = await backendRequest(
      `/admin/users/${encodeURIComponent(userId)}/reset-password`,
      { method: "POST", body: JSON.stringify({ password }) },
      token,
    );
  } catch {
    return { status: "error", message: "The user service is temporarily unavailable." };
  }
  if (!response.ok) {
    return { status: "error", message: await readApiError(response) };
  }
  return { status: "success", message: "Password updated and existing tokens invalidated." };
}
