import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

function demoPatientCredentials() {
  const realm = JSON.parse(readFileSync("../../infrastructure/keycloak/patient-health-realm.json", "utf8"));
  const user = realm.users.find((item: { username: string }) => item.username === "demo.patient");
  if (!user?.credentials?.[0]?.value) throw new Error("Demo patient credentials not found");
  return { username: user.username, password: user.credentials[0].value };
}

test("research conversations can be created, renamed, searched and deleted", async ({ page }) => {
  await page.goto("/research");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/realms\/patient-health\/protocol\/openid-connect\/auth/);
  const credentials = demoPatientCredentials();
  await page.locator("#username").fill(credentials.username);
  await page.locator("#password").fill(credentials.password);
  await page.locator("#kc-login").click();

  await expect(page.getByRole("heading", { name: "Public health research assistant" })).toBeVisible();
  const title = `E2E research ${Date.now()}`;
  await page.getByRole("button", { name: "New research" }).click();
  const original = page.getByRole("button", { name: "Rename New research session" }).first();
  await expect(original).toBeVisible();

  page.once("dialog", (dialog) => void dialog.accept(title));
  await original.click();
  await expect(page.getByRole("button", { name: title, exact: true })).toBeVisible();

  await page.getByRole("searchbox", { name: "Search research history" }).fill(title);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("button", { name: title, exact: true })).toBeVisible();

  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: `Delete ${title}` }).click();
  await expect(page.getByRole("button", { name: title, exact: true })).not.toBeVisible();

  await page.getByRole("button", { name: "Clear" }).click();
  await expect(page.getByRole("button", { name: "New research" })).toBeEnabled();
});
