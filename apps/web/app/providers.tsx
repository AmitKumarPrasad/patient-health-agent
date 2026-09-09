"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getKeycloak } from "./keycloak";

type AuthContextValue = {
  authenticated: boolean;
  ready: boolean;
  roles: string[];
  hasRole: (role: string) => boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readRoles(): string[] {
  const keycloak = getKeycloak();
  const parsed = keycloak.tokenParsed as
    | {
        realm_access?: { roles?: string[] };
        resource_access?: Record<string, { roles?: string[] }>;
      }
    | undefined;
  const roles = new Set<string>(parsed?.realm_access?.roles ?? []);
  for (const client of Object.values(parsed?.resource_access ?? {})) {
    for (const role of client.roles ?? []) roles.add(role);
  }
  return [...roles];
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [roles, setRoles] = useState<string[]>([]);

  useEffect(() => {
    const keycloak = getKeycloak();
    keycloak
      .init({
        onLoad: "check-sso",
        pkceMethod: "S256",
        checkLoginIframe: false,
        silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      })
      .then((isAuthenticated: boolean) => {
        setAuthenticated(isAuthenticated);
        setRoles(isAuthenticated ? readRoles() : []);
        setReady(true);
      })
      .catch(() => setReady(true));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      authenticated,
      ready,
      roles,
      hasRole: (role: string) => roles.includes(role),
      login: () => getKeycloak().login(),
      logout: () => getKeycloak().logout({ redirectUri: window.location.origin }),
    }),
    [authenticated, ready, roles],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
