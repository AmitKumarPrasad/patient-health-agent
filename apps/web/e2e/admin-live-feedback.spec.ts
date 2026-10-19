import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

function demoAdminCredentials() {
  const realm = JSON.parse(readFileSync("../../infrastructure/keycloak/patient-health-realm.json", "utf8"));
  const user = realm.users.find((item: { username: string }) => item.username === "demo.admin");
  if (!user?.credentials?.[0]?.value) throw new Error("Demo admin credentials not found");
  return { username: user.username, password: user.credentials[0].value };
}

test("admin audit operation feedback is announced to screen readers", async ({ page }) => {
  let processingAttempts = 0;

  await page.route("**/api/admin/audit*", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/admin/notifications/process", (route) => {
    processingAttempts += 1;
    if (processingAttempts === 1) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ processed: 3 }),
      });
    }
    return route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Synthetic processing failure" }),
    });
  });

  await page.goto("/");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/realms\/patient-health\/protocol\/openid-connect\/auth/);

  const credentials = demoAdminCredentials();
  await page.locator("#username").fill(credentials.username);
  await page.locator("#password").fill(credentials.password);
  await page.locator("#kc-login").click();

  await page.goto("/admin/audit");
  await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();

  const processButton = page.getByRole("button", { name: "Process due notifications" });
  await processButton.click();
  await expect(page.getByRole("status")).toHaveText("3 due notification(s) processed.");

  await processButton.click();
  await expect(page.getByRole("alert")).toHaveText("Synthetic processing failure");
});
