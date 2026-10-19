import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024;

function demoPatientCredentials() {
  const realm = JSON.parse(
    readFileSync("../../infrastructure/keycloak/patient-health-realm.json", "utf8"),
  );
  const user = realm.users.find((item: { username: string }) => item.username === "demo.patient");
  if (!user?.credentials?.[0]?.value) throw new Error("Demo patient credentials not found");
  return { username: user.username, password: user.credentials[0].value };
}

test("patient gets an accessible warning before choosing a record larger than 10 MB", async ({ page }) => {
  let uploadRequests = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && new URL(request.url()).pathname.endsWith("/api/documents")) {
      uploadRequests += 1;
    }
  });

  await page.goto("/");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((url) => url.pathname.includes("/realms/patient-health/protocol/openid-connect/auth"));

  const credentials = demoPatientCredentials();
  await page.locator("#username").fill(credentials.username);
  await page.locator("#password").fill(credentials.password);
  await page.locator("#kc-login").click();

  await expect(page.getByRole("heading", { name: /Welcome, Demo/i })).toBeVisible();
  const records = page.locator("#records");
  const fileInput = records.getByLabel("Choose a record");
  await expect(records.getByText("PDF, JPG, PNG, or text files up to 10 MB.")).toBeVisible();

  const retry = test.info().retry;
  await fileInput.setInputFiles({
    name: `synthetic-oversize-${retry}.txt`,
    mimeType: "text/plain",
    buffer: Buffer.alloc(MAX_DOCUMENT_BYTES + 1, 65),
  });

  await expect(records.getByRole("alert")).toHaveText(
    "This file is larger than the 10 MB upload limit. Choose a smaller file.",
  );
  await expect(records.getByRole("button", { name: "Upload record" })).toBeDisabled();
  expect(uploadRequests).toBe(0);

  await fileInput.setInputFiles({
    name: `synthetic-at-limit-${retry}.txt`,
    mimeType: "text/plain",
    buffer: Buffer.alloc(MAX_DOCUMENT_BYTES, 65),
  });
  await expect(records.getByRole("alert")).toHaveCount(0);
  await expect(records.getByRole("button", { name: "Upload record" })).toBeEnabled();
  expect(uploadRequests).toBe(0);
});
