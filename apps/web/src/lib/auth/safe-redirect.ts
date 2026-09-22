export function getSafeNextPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/dashboard";
  }

  try {
    const parsed = new URL(value, "http://cyverse.local");
    if (parsed.origin !== "http://cyverse.local") {
      return "/dashboard";
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return "/dashboard";
  }
}
