import { expect, test } from "@playwright/test";

import { startFakeBackend } from "./fake-backend.mjs";

let stopFakeBackend: (() => Promise<void>) | undefined;

test.beforeAll(async () => {
  stopFakeBackend = await startFakeBackend();
});

test.afterAll(async () => {
  await stopFakeBackend?.();
});

test("redirects anonymous visitors to sign in", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard/);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
});

test("shows a generic error and signs in with valid credentials", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("incorrect-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.locator(".form-message--error")).toHaveText("Invalid username or password.");

  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await Promise.all([
    page.waitForURL(/\/dashboard$/),
    page.getByRole("button", { name: /sign in/i }).click(),
  ]);
  await expect(page.getByRole("heading", { name: /Hello, Nguyen/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "User Management" })).toBeVisible();
});

test("opens account settings from the profile menu and updates personal details", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await Promise.all([
    page.waitForURL(/\/dashboard$/),
    page.getByRole("button", { name: /sign in/i }).click(),
  ]);

  await page.getByLabel("Open account menu").click();
  await page.getByRole("link", { name: /account settings/i }).click();
  await expect(page).toHaveURL(/\/settings\/account/);
  await expect(page.getByRole("heading", { name: "Account Settings" })).toBeVisible();
  await expect(page.getByLabel("Username")).toBeDisabled();

  await page.locator('input[name="team"]').fill("Platform");
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByText("Profile details updated.")).toBeVisible();
});

test("administrator can create and deactivate a user", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await Promise.all([
    page.waitForURL(/\/dashboard$/),
    page.getByRole("button", { name: /sign in/i }).click(),
  ]);
  await page.getByRole("link", { name: "User Management" }).click();
  await expect(page).toHaveURL(/\/admin\/users/);
  await expect(page.locator(".route-loading")).toBeVisible();
  await expect(page.getByRole("heading", { name: "User Management" })).toBeVisible();

  await page.getByRole("button", { name: /new user/i }).click();
  const dialog = page.getByRole("dialog", { name: /create user/i });
  await dialog.getByLabel("Username").fill("research.user");
  await dialog.getByLabel("Display name").fill("Research User");
  await dialog.locator('input[name="team"]').fill("Research Team");
  await dialog.getByLabel("Password").fill("temporary-password");
  await dialog.getByRole("button", { name: "Create user" }).click();
  await expect(page.getByText("@research.user").first()).toBeVisible();

  const row = page.getByRole("row").filter({ hasText: "@research.user" }).first();
  await row.getByRole("button", { name: "Edit" }).click();
  const editDialog = page.getByRole("dialog", { name: "Edit user" });
  await expect(editDialog).toBeVisible();
  await expect(editDialog.locator("form")).toHaveCSS("display", "grid");
  await editDialog.getByRole("button", { name: "Close dialog" }).click();

  page.once("dialog", (confirmation) => confirmation.accept());
  await row.getByRole("button", { name: "Deactivate" }).click();
  await expect(row.getByText("Inactive").first()).toBeVisible();
});

test("research session survives reload and completes with safe paper links", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await Promise.all([
    page.waitForURL(/\/dashboard$/),
    page.getByRole("button", { name: /sign in/i }).click(),
  ]);

  await page.getByRole("link", { name: "AI Research Tool" }).click();
  await expect(page.getByRole("heading", { name: "AI Research Tool" })).toBeVisible();
  await page.getByRole("button", { name: "Advanced settings" }).click();
  await page.getByLabel("arXiv raw papers").fill("25");
  await page.reload();
  await page.getByRole("button", { name: "Advanced settings" }).click();
  await expect(page.getByLabel("arXiv raw papers")).toHaveValue("25");
  await page.getByLabel("Time range").selectOption("from-2025");
  await expect(page.getByLabel("Time range")).toHaveValue("from-2025");

  await page.getByLabel("Research question").fill("Explainable multimodal deepfake detection");
  await page.getByRole("button", { name: /search papers/i }).click();
  await expect(page).toHaveURL(/\/tools\/research\/[0-9a-f-]+$/);
  await expect(page.getByText(/waiting in queue/i)).toBeVisible();

  await expect(
    page.getByRole("heading", { name: "Explainable Deepfake Detection with Multimodal Evidence" }),
  ).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Nghiên cứu đề xuất phương pháp/)).toBeVisible();
  const openLink = page.getByRole("link", { name: /open pdf/i });
  await expect(openLink).toHaveAttribute("target", "_blank");
  await expect(openLink).toHaveAttribute("rel", /noopener/);

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Explainable Deepfake Detection with Multimodal Evidence" }),
  ).toBeVisible();

  await page.getByRole("button", { name: /more options for explainable multimodal/i }).click();
  page.once("dialog", (dialog) => dialog.accept("Renamed deepfake research"));
  await page.getByRole("menuitem", { name: "Rename" }).click();
  await expect(page.getByRole("heading", { name: "Renamed deepfake research" })).toBeVisible();

  await page.getByRole("button", { name: /more options for renamed deepfake research/i }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("menuitem", { name: "Delete" }).click();
  await expect(page).toHaveURL(/\/tools\/research$/);
  await expect(page.getByText("Your research sessions will appear here.")).toBeVisible();
});
