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

test("Threads collection saves settings, survives reload, and exports results", async ({ page }, testInfo) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/dashboard$/);
  await page.getByRole("link", { name: "Threads Scraper" }).click();
  await page.waitForURL(/\/tools\/threads$/);
  await expect(page.getByRole("heading", { name: "Threads Scraper" })).toBeVisible({ timeout: 20000 });
  await expect(page.getByRole("button", { name: "Start collection" })).toBeEnabled();
  await page.screenshot({ path: testInfo.outputPath("threads-desktop.png"), fullPage: true });
  const searchSettings = page.locator("#threads-search-settings-label").locator("..");
  await searchSettings.getByRole("button", { name: "50", exact: true }).click();
  await searchSettings.getByRole("button", { name: "Top posts", exact: true }).click();
  await page.reload();
  await expect(searchSettings.getByRole("button", { name: "50", exact: true })).toHaveAttribute("data-active", "true");
  await expect(searchSettings.getByRole("button", { name: "Top posts", exact: true })).toHaveAttribute("data-active", "true");
  await page.getByLabel("Search question or keywords").fill("Quiet cafes for reading");
  await page.getByRole("button", { name: "Start collection" }).click();
  await expect(page).toHaveURL(/\/tools\/threads\/[0-9a-f-]+$/);
  await page.reload();
  await expect(page.getByText("A quiet cafe with a reading corner and great coffee.", { exact: true })).toBeVisible({ timeout: 20000 });
  const source = page.getByRole("link", { name: "Open post" });
  await expect(source).toHaveAttribute("rel", "noopener noreferrer");
  await expect(page.getByText("2 collected comments", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Weekday mornings are the quietest.")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Reuse settings/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Markdown/ })).toHaveCount(0);
  await page.getByPlaceholder(/Search within results/).fill("missing phrase");
  await expect(page.getByRole("heading", { name: "No posts to show" })).toBeVisible();
  await page.getByPlaceholder(/Search within results/).fill("");
  await page.screenshot({ path: testInfo.outputPath("threads-results.png"), fullPage: true });
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "JSON", exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/^threads-.*\.json$/);
});

test("Threads can cancel a queued collection and works on a small screen", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/dashboard$/);
  await page.goto("/tools/threads");
  await page.getByLabel("Search question or keywords").fill("Another cafe collection");
  await page.getByRole("button", { name: "Start collection" }).click();
  await expect(page).toHaveURL(/\/tools\/threads\/[0-9a-f-]+$/);
  await page.getByRole("button", { name: "Cancel collection", exact: true }).click();
  await expect(page.getByText("This collection was cancelled. Start a new collection to try again.")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("threads-mobile.png"), fullPage: true });
  const overflow = await page.evaluate(() => Array.from(document.querySelectorAll("main *"))
    .filter((element) => element.getBoundingClientRect().right > window.innerWidth + 1)
    .map((element) => ({ tag: element.tagName, className: element.className, right: element.getBoundingClientRect().right }))
    .slice(0, 12));
  expect(overflow).toEqual([]);
  await page.reload();
  await expect(page.getByText("This collection was cancelled. Start a new collection to try again.")).toBeVisible();
});

test("Threads sharing, background collection, TXT download, and permanent deletion", async ({ page, context }, testInfo) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/dashboard$/);
  await page.goto("/tools/threads");
  await expect(page.getByLabel("New session visibility", { exact: true })).toHaveCount(0);
  await page.getByLabel("Search question or keywords").fill("Background TXT collection");
  await page.getByRole("button", { name: "Start collection" }).click();
  await expect(page).toHaveURL(/\/tools\/threads\/[0-9a-f-]+$/);
  const sessionUrl = page.url();
  await expect(page.getByLabel("Saved session visibility")).toHaveValue("public");
  await page.getByLabel("Saved session visibility").selectOption("private");
  await expect(page.getByLabel("Saved session visibility")).toHaveValue("private");
  await page.close();

  const restored = await context.newPage();
  await restored.goto(sessionUrl);
  await expect(restored.getByLabel("Saved session visibility")).toHaveValue("private");
  await expect(restored.getByText("A quiet cafe with a reading corner and great coffee.", { exact: true })).toBeVisible({ timeout: 20000 });
  await restored.getByText("Session metadata", { exact: true }).click();
  await expect(restored.getByText("Nguyen Anh", { exact: true }).last()).toBeVisible();
  const download = restored.waitForEvent("download");
  await restored.getByRole("link", { name: "Text", exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/^threads-.*\.txt$/);
  await restored.setViewportSize({ width: 390, height: 844 });
  await expect(restored.getByRole("link", { name: "Text", exact: true })).toBeVisible();
  await restored.screenshot({ path: testInfo.outputPath("threads-sharing-mobile.png"), fullPage: true });
  const workspaceSize = await restored.locator("main").last().evaluate((element) => ({
    width: element.clientWidth, scrollWidth: element.scrollWidth,
    overflowing: Array.from(element.querySelectorAll("*")).filter((child) => child.getBoundingClientRect().right > element.getBoundingClientRect().right + 1)
      .map((child) => ({ tag: child.tagName, className: child.className, width: child.getBoundingClientRect().width })).slice(0, 12),
  }));
  expect(workspaceSize.scrollWidth, JSON.stringify(workspaceSize)).toBeLessThanOrEqual(workspaceSize.width);
  await restored.getByLabel("Saved session visibility").selectOption("public");
  await expect(restored.getByLabel("Saved session visibility")).toHaveValue("public");
  restored.once("dialog", (dialog) => dialog.accept());
  await restored.getByRole("button", { name: "Delete session", exact: true }).click();
  await expect(restored).toHaveURL(/\/tools\/threads$/);
  await expect(restored.getByRole("button", { name: /Background TXT collection/ })).toHaveCount(0);
  await restored.goto(sessionUrl);
  await expect(restored.getByRole("alert").filter({ hasText: "Threads run not found." })).toBeVisible();
});


test("Threads history sits on the left and panel preferences survive reload", async ({ page }, testInfo) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/dashboard$/);
  await page.goto("/tools/threads");
  const history = page.getByRole("complementary", { name: "Session history" });
  const settings = page.getByRole("region", { name: "Search settings" });
  await expect(page.getByRole("button", { name: "Start collection" })).toBeEnabled();
  const railBox = await history.boundingBox();
  const settingsBox = await settings.boundingBox();
  expect(railBox && settingsBox && railBox.x < settingsBox.x).toBeTruthy();
  await page.getByRole("button", { name: "Collapse search settings" }).click();
  await expect(page.getByLabel("Search question or keywords")).not.toBeVisible();
  await page.getByRole("button", { name: "Collapse history" }).click();
  await expect(history).toHaveAttribute("data-collapsed", "true");
  await page.reload();
  await expect(page.getByRole("button", { name: "Expand search settings" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Expand history" })).toBeVisible();
  await page.getByRole("button", { name: "Expand history" }).click();
  await page.getByRole("button", { name: "Expand search settings" }).click();
  await expect(page.getByLabel("Search question or keywords")).toBeVisible();
  await expect(settings.getByRole("combobox")).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("threads-history-left.png"), fullPage: true });
});
