export type UserRole = "admin" | "member";

export interface AuthUser {
  id: string;
  username: string;
  display_name: string;
  team: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  access_expires_at: string;
  refresh_expires_at: string;
  user: AuthUser;
}

export type TokenPairResponse = Omit<LoginResponse, "user">;

export function isTokenPairResponse(value: unknown): value is TokenPairResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  const validToken = (token: unknown) =>
    typeof token === "string" && token.length > 0 && token.length <= 4096;
  const validDate = (date: unknown) =>
    typeof date === "string" && Number.isFinite(Date.parse(date));
  return (
    validToken(candidate.access_token) &&
    validToken(candidate.refresh_token) &&
    candidate.token_type === "bearer" &&
    validDate(candidate.access_expires_at) &&
    validDate(candidate.refresh_expires_at)
  );
}

export interface UserListResponse {
  items: AuthUser[];
  total: number;
  page: number;
  page_size: number;
  current_user_id: string;
}

export function isAuthUser(value: unknown): value is AuthUser {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.username === "string" &&
    typeof candidate.display_name === "string" &&
    (typeof candidate.team === "string" || candidate.team === null) &&
    (candidate.role === "admin" || candidate.role === "member") &&
    typeof candidate.is_active === "boolean" &&
    typeof candidate.created_at === "string" &&
    typeof candidate.updated_at === "string"
  );
}

export function isUserListResponse(value: unknown): value is UserListResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    Array.isArray(candidate.items) &&
    candidate.items.every(isAuthUser) &&
    typeof candidate.total === "number" &&
    Number.isInteger(candidate.total) &&
    candidate.total >= 0 &&
    typeof candidate.page === "number" &&
    Number.isInteger(candidate.page) &&
    candidate.page >= 1 &&
    typeof candidate.page_size === "number" &&
    Number.isInteger(candidate.page_size) &&
    candidate.page_size >= 1 &&
    typeof candidate.current_user_id === "string"
  );
}

export interface ActionState {
  status: "idle" | "success" | "error";
  message: string;
  username?: string;
}

export const INITIAL_ACTION_STATE: ActionState = { status: "idle", message: "" };
