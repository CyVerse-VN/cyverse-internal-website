export const ACCESS_TOKEN_COOKIE_NAME = "cyverse_access_token";
export const REFRESH_TOKEN_COOKIE_NAME = "cyverse_refresh_token";

export function authCookieOptions(expiresAt: string | Date) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(expiresAt),
  };
}
