import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

function demoPatientCredentials() {
  const realm = JSON.parse(readFileSync("../../infrastructure/keycloak/patient-health-realm.json", "utf8"));
  const user = realm.users.find((item: { username: string }) => item.username === "demo.patient");
  if (!user?.credentials?.[0]?.value) throw new Error("Demo patient credentials not found");
  return { username: user.username, password: user.credentials[0].value };
}

test("research responses are announced in an accessible conversation log", async ({ page }) => {
  let releaseResponse!: () => void;
  let markMessageRequestSeen!: () => void;
  const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve; });
  const messageRequestSeen = new Promise<void>((resolve) => { markMessageRequestSeen = resolve; });
  const answer = "Preventive care can help find health concerns early and reduce the risk of illness.";

  await page.route("**/api/research/sessions/*/messages", async (route) => {
    const request = route.request();
    if (request.method() !== "POST") {
      await route.continue();
      return;
    }
    const path = new URL(request.url()).pathname;
    const sessionId = path.split("/").at(-2);
    if (!sessionId) {
      await route.continue();
      return;
    }
    markMessageRequestSeen();
    await responseGate;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: sessionId,
        title: "E2E research session",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:01:00Z",
        messages: [
          {
            id: "e2e-user-message",
            role: "user",
            content: "What is preventive care?",
            sources: [],
            created_at: "2026-01-01T00:00:30Z",
          },
          {
            id: "e2e-assistant-message",
            role: "assistant",
            content: answer,
            sources: [],
            created_at: "2026-01-01T00:01:00Z",
          },
        ],
      }),
    });
  });

  await page.goto("/research");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/realms\/patient-health\/protocol\/openid-connect\/auth/);
  const credentials = demoPatientCredentials();
  await page.locator("#username").fill(credentials.username);
  await page.locator("#password").fill(credentials.password);
  await page.locator("#kc-login").click();

  const log = page.getByRole("log", { name: "Research conversation" });
  await expect(log).toBeVisible();
  await expect(log).toHaveAttribute("aria-live", "polite");
  await expect(log).toHaveAttribute("aria-atomic", "false");
  await expect(log).toHaveAttribute("aria-relevant", "additions text");
  await expect(log).toHaveAttribute("aria-busy", "false");

  const question = page.locator("textarea[placeholder^='e.g. What is the difference']");
  await expect(question).toBeEnabled({ timeout: 30_000 });
  await question.fill("What is preventive care?");
  await page.getByRole("button", { name: "Research", exact: true }).click();
  try {
    await messageRequestSeen;
    await expect(log).toHaveAttribute("aria-busy", "true");
  } finally {
    releaseResponse();
  }

  await expect(log).toContainText(answer);
  await expect(log).toHaveAttribute("aria-busy", "false");
});
