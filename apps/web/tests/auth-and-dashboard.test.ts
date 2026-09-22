import { describe, expect, it } from "vitest";

import { filterTools, popularTools } from "../src/features/dashboard/dashboard-view";
import { getSafeNextPath } from "../src/lib/auth/safe-redirect";
import { isUserListResponse } from "../src/lib/auth/types";
import { isValidUsername, normalizeUsername } from "../src/lib/auth/validation";

describe("getSafeNextPath", () => {
  it("accepts local application paths", () => {
    expect(getSafeNextPath("/admin/users?page=2")).toBe("/admin/users?page=2");
  });

  it("rejects external and protocol-relative paths", () => {
    expect(getSafeNextPath("https://example.com/admin")).toBe("/dashboard");
    expect(getSafeNextPath("//example.com/admin")).toBe("/dashboard");
  });
});

describe("username validation", () => {
  it("normalizes valid usernames to lowercase", () => {
    expect(normalizeUsername("  Nguyen.Anh  ")).toBe("nguyen.anh");
    expect(isValidUsername("nguyen.anh_01")).toBe(true);
  });

  it("rejects usernames containing whitespace", () => {
    expect(isValidUsername("nguyen anh")).toBe(false);
  });
});

describe("filterTools", () => {
  it("returns all tools for an empty search", () => {
    expect(filterTools("")).toEqual(popularTools);
  });

  it("matches names and descriptions without case sensitivity", () => {
    expect(filterTools("VIDEO").map((tool) => tool.name)).toEqual([
      "Deepfake Detection",
      "Video Analysis",
    ]);
    expect(filterTools("attention").map((tool) => tool.name)).toEqual([
      "Explainability Viewer",
    ]);
  });
});

describe("isUserListResponse", () => {
  const user = {
    id: "00000000-0000-4000-8000-000000000001",
    username: "admin",
    display_name: "Admin User",
    team: "Platform",
    role: "admin",
    is_active: true,
    created_at: "2026-09-12T00:00:00Z",
    updated_at: "2026-09-12T00:00:00Z",
  };

  it("accepts a complete paginated user response", () => {
    expect(
      isUserListResponse({
        items: [user],
        total: 1,
        page: 1,
        page_size: 20,
        current_user_id: user.id,
      }),
    ).toBe(true);
  });

  it("rejects a response without the current user identifier", () => {
    expect(isUserListResponse({ items: [user], total: 1, page: 1, page_size: 20 })).toBe(false);
  });
});
