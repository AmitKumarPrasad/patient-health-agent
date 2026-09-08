import { expect, test } from "@playwright/test";

test("patient can sign in, find a provider, book, list, and cancel an appointment", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Secure healthcare appointment management" })).toBeVisible();

  await page.getByRole("button", { name: "Continue to login" }).click();
  await page.waitForURL(/\/realms\/patient-health\/protocol\/openid-connect\/auth/);

  await page.locator("#username").fill("demo.patient");
  await page.locator("#password").fill("ChangeMe!Patient123");
  await page.locator("#kc-login").click();

  await expect(page.getByRole("heading", { name: /Welcome, Demo/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Find a provider" })).toBeVisible();

  const records = page.locator("#records");
  const fileInput = records.locator("#record-file");
  await fileInput.setInputFiles({
    name: "e2e-record.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic E2E patient record for upload testing."),
  });
  await records.getByPlaceholder("Category, e.g. lab report").fill("E2E test record");
  await records.getByPlaceholder("Short description (optional)").fill("Synthetic upload used by Playwright.");
  await records.getByRole("button", { name: "Upload record" }).click();
  await expect(records.getByText("e2e-record.txt", { exact: true })).toBeVisible();
  await expect(records.getByText("E2E test record", { exact: true })).toBeVisible();

  await records.getByPlaceholder("Search filename, category or description").fill("e2e-record.txt");
  await records.getByRole("button", { name: "Search", exact: true }).click();
  await expect(records.getByText("e2e-record.txt", { exact: true })).toBeVisible();

  const providers = page.locator("#providers");
  await page.getByPlaceholder("Specialty, e.g. cardiology").fill("General Medicine");
  await providers.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("Demo Provider", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "View availability" }).click();
  await expect(page.getByRole("heading", { name: /Availability: Demo Provider/ })).toBeVisible();

  await page.locator('input[type="date"]').fill("2026-09-09");
  await expect(page.getByRole("button", { name: /10:00/ })).toBeVisible();
  await page.getByRole("button", { name: /10:00/ }).click();

  const appointments = page.locator("#appointments");
  await expect(appointments.getByText("scheduled", { exact: true })).toBeVisible();
  await expect(appointments.getByText("10:00", { exact: false })).toBeVisible();

  await appointments.getByRole("button", { name: "Cancel appointment" }).click();
  await expect(appointments.getByText("cancelled", { exact: true })).toBeVisible();
});
