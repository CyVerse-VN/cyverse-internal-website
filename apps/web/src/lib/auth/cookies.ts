export const ACCESS_TOKEN_COOKIE_NAME = "cyverse_access_token";
export const REFRESH_TOKEN_COOKIE_NAME = "cyverse_refresh_token";

export function authCookieOptions(expiresAt: string | Date, maxAgeSeconds?: number) {
  const expires = new Date(expiresAt);
  const calculatedMaxAge = Math.max(0, Math.floor((expires.getTime() - Date.now()) / 1000));
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production" && process.env.COOKIE_SECURE !== "false",
    path: "/",
    expires,
    maxAge: maxAgeSeconds ?? (Number.isFinite(calculatedMaxAge) ? calculatedMaxAge : undefined),
  };
}

