import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

function demoPatientCredentials() {
  const realm = JSON.parse(readFileSync("../../infrastructure/keycloak/patient-health-realm.json", "utf8"));
  const user = realm.users.find((item: { username: string }) => item.username === "demo.patient");
  if (!user?.credentials?.[0]?.value) throw new Error("Demo patient credentials not found");
  return { username: user.username, password: user.credentials[0].value };
}

test("patient assistant message areas have persistent accessible labels", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/realms\/patient-health\/protocol\/openid-connect\/auth/);

  const credentials = demoPatientCredentials();
  await page.locator("#username").fill(credentials.username);
  await page.locator("#password").fill(credentials.password);
  await page.locator("#kc-login").click();

  await expect(page.getByRole("heading", { name: /Welcome/i })).toBeVisible();
  const appointmentQuestion = page.getByRole("textbox", { name: "Question for appointment assistant" });
  const recordsQuestion = page.getByRole("textbox", { name: "Question about my records" });
  await expect(appointmentQuestion).toBeVisible();
  await expect(recordsQuestion).toBeVisible();

  await appointmentQuestion.fill("Help me find a cardiologist.");
  await expect(page.getByRole("textbox", { name: "Question for appointment assistant" })).toHaveValue("Help me find a cardiologist.");
  await recordsQuestion.fill("Find my latest lab report.");
  await expect(page.getByRole("textbox", { name: "Question about my records" })).toHaveValue("Find my latest lab report.");
});
