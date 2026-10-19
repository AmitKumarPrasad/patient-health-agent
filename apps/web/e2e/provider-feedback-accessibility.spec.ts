import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

function demoProviderCredentials() {
  const realm = JSON.parse(readFileSync("../../infrastructure/keycloak/patient-health-realm.json", "utf8"));
  const user = realm.users.find((item: { username: string }) => item.username === "demo.provider");
  if (!user?.credentials?.[0]?.value) throw new Error("Demo provider credentials not found");
  return { username: user.username, password: user.credentials[0].value };
}

test("provider availability success is announced to assistive technology", async ({ page }) => {
  await page.route("**/api/providers/**/availability**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "POST" && path === "/api/providers/me/availability") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "e2e-availability",
          provider_id: "e2e-provider",
          available_date: "2026-12-01",
          start_time: "10:00",
          end_time: "10:30",
          is_available: true,
        }),
      });
      return;
    }
    if (request.method() === "GET" && path.endsWith("/availability")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      return;
    }
    await route.continue();
  });

  await page.goto("/provider");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/realms\/patient-health\/protocol\/openid-connect\/auth/);
  const credentials = demoProviderCredentials();
  await page.locator("#username").fill(credentials.username);
  await page.locator("#password").fill(credentials.password);
  await page.locator("#kc-login").click();

  await expect(page.getByRole("heading", { name: "Manage availability" })).toBeVisible({ timeout: 30_000 });
  await page.getByLabel("Date").fill("2026-12-01");
  await page.getByLabel("Start").fill("10:00");
  await page.getByLabel("End").fill("10:30");
  await page.getByRole("button", { name: "Add slot", exact: true }).click();

  await expect(page.getByRole("status")).toHaveText("Availability slot added.");
});
