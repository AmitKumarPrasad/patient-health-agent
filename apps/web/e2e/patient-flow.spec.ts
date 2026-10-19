import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

function demoPatientCredentials() {
  const realm = JSON.parse(
    readFileSync("../../infrastructure/keycloak/patient-health-realm.json", "utf8"),
  );
  const user = realm.users.find((item: { username: string }) => item.username === "demo.patient");
  if (!user?.credentials?.[0]?.value) throw new Error("Demo patient credentials not found");
  return { username: user.username, password: user.credentials[0].value };
}

test("patient can sign in, manage records, book, join, and cancel an appointment", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/realms\/patient-health\/protocol\/openid-connect\/auth/);

  const credentials = demoPatientCredentials();
  await page.locator("#username").fill(credentials.username);
  await page.locator("#password").fill(credentials.password);
  await page.locator("#kc-login").click();

  await expect(page.getByRole("heading", { name: /Welcome, Demo/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Find a provider" })).toBeVisible();

  const appointments = page.locator("#appointments");
  const e2eAppointmentReason = "Synthetic Playwright cancellation retry check";
  const previousTestAppointments = appointments.locator(".list-item").filter({ hasText: e2eAppointmentReason });
  for (let index = 0; index < await previousTestAppointments.count(); index += 1) {
    const previousAppointment = previousTestAppointments.nth(index);
    const previousCancelButton = previousAppointment.getByRole("button", { name: "Cancel appointment" });
    if (await previousCancelButton.count()) {
      await previousCancelButton.click();
      const previousConfirmation = page.getByRole("dialog", { name: "Cancel appointment?" });
      await previousConfirmation.getByRole("button", { name: "Confirm cancellation" }).click();
      await expect(previousAppointment.getByText("cancelled", { exact: true })).toBeVisible();
    }
  }

  const records = page.locator("#records");
  const fileInput = records.locator("#record-file");
  const retry = test.info().retry;
  const recordFilename = `e2e-record-${retry}.txt`;
  const recordCategory = `E2E test record ${retry}`;
  await fileInput.setInputFiles({
    name: recordFilename,
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic E2E patient record for lifecycle testing."),
  });
  await records.getByPlaceholder("Category, e.g. lab report").fill(recordCategory);
  await records.getByPlaceholder("Short description (optional)").fill("Synthetic upload used by Playwright.");
  await records.getByRole("button", { name: "Upload record" }).click();
  await expect(records.getByText(recordFilename, { exact: true })).toBeVisible();
  await expect(records.getByText(recordCategory, { exact: true })).toBeVisible();

  let recordItem = records.locator(".list-item").filter({ hasText: recordFilename });
  await expect(recordItem.getByRole("button", { name: "Download" })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await recordItem.getByRole("button", { name: "Download" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(recordFilename);

  await records.getByPlaceholder("Search filename, category or description").fill(recordFilename);
  await records.getByRole("button", { name: "Search", exact: true }).click();
  await expect(records.getByText(recordFilename, { exact: true })).toBeVisible();

  recordItem = records.locator(".list-item").filter({ hasText: recordFilename });
  await expect(recordItem.getByRole("button", { name: "Delete" })).toBeVisible();
  page.once("dialog", (dialog) => void dialog.accept());
  await recordItem.getByRole("button", { name: "Delete" }).click();
  await expect(records.getByText(recordFilename, { exact: true })).not.toBeVisible();

  const providers = page.locator("#providers");
  await page.getByPlaceholder("Specialty, e.g. cardiology").fill("General Medicine");
  await providers.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("Demo Provider", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "View availability" }).click();
  await expect(page.getByRole("heading", { name: /Availability: Demo Provider/ })).toBeVisible();

  await page.locator('input[type="date"]').fill("2026-09-09");
  await expect(page.getByRole("button", { name: /10:00/ })).toBeVisible();
  await page.getByPlaceholder("Reason for visit (optional)").fill(e2eAppointmentReason);
  await page.getByRole("button", { name: /10:00/ }).click();
  const bookedAppointment = appointments.locator(".list-item").filter({ hasText: e2eAppointmentReason });
  await expect(bookedAppointment.getByText("scheduled", { exact: true })).toBeVisible();
  await expect(bookedAppointment.getByText("10:00", { exact: false })).toBeVisible();
  await expect(bookedAppointment.getByRole("button", { name: "Join video consultation" })).toBeVisible();

  const cancelButton = bookedAppointment.getByRole("button", { name: "Cancel appointment" });
  await cancelButton.click();
  const cancellationDialog = page.getByRole("dialog", { name: "Cancel appointment?" });
  await expect(cancellationDialog).toContainText(/^Are you sure you want to cancel the appointment scheduled for /);
  await cancellationDialog.getByRole("button", { name: "Keep appointment" }).click();

  await expect(bookedAppointment.getByText("scheduled", { exact: true })).toBeVisible();
  await expect(cancelButton).toBeVisible();

  await cancelButton.click();
  await page.getByRole("dialog", { name: "Cancel appointment?" })
    .getByRole("button", { name: "Confirm cancellation" }).click();
  await expect(bookedAppointment.getByText("cancelled", { exact: true })).toBeVisible();
  await expect(bookedAppointment.getByRole("button", { name: "Join video consultation" })).not.toBeVisible();
});
