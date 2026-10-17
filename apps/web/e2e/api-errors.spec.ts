import { expect, test } from "@playwright/test";
import { apiErrorMessage, networkErrorMessage } from "../lib/api-errors";

test("API errors distinguish expired sessions, permissions and unavailable services", () => {
  expect(apiErrorMessage(401)).toMatch(/login session has expired/i);
  expect(apiErrorMessage(403)).toMatch(/not allowed/i);
  expect(apiErrorMessage(429)).toMatch(/too many requests/i);
  expect(apiErrorMessage(503, "DATABASE_PASSWORD=secret")).toMatch(/temporarily unavailable/i);
  expect(apiErrorMessage(503, "DATABASE_PASSWORD=secret")).not.toContain("secret");
  expect(apiErrorMessage(500, "private stack trace")).not.toContain("private stack trace");
  expect(apiErrorMessage(422, "Field is required")).toBe("Field is required");
});

test("network errors do not leak raw browser or service internals", () => {
  expect(networkErrorMessage(new TypeError("Failed to fetch https://internal.example:8080"))).toMatch(/cannot connect/i);
  expect(networkErrorMessage(new TypeError("Failed to fetch https://internal.example:8080"))).not.toContain("internal.example");
  expect(networkErrorMessage(Object.assign(new Error("canceled"), { name: "AbortError" }))).toMatch(/cancelled/i);
});
