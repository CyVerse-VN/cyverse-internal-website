export const USERNAME_RULE = /^[A-Za-z0-9._-]{3,64}$/;

export function normalizeUsername(value: string): string {
  return value.trim().toLowerCase();
}

export function isValidUsername(value: string): boolean {
  return USERNAME_RULE.test(value);
}
