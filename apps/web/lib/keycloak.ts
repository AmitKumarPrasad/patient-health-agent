"use client";

import Keycloak from "keycloak-js";

let client: Keycloak | null = null;

export function getKeycloak(): Keycloak {
  if (typeof window === "undefined") {
    throw new Error("Keycloak can only be initialized in the browser");
  }

  if (!client) {
    client = new Keycloak({
      url: process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://localhost:8080",
      realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "patient-health",
      clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "patient-health-web",
    });
  }

  return client;
}
