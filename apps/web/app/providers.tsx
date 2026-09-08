"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "./react";
import { getKeycloak } from "./keycloak";

type AuthContextValue = {
  authenticated: boolean;
  ready: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

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
        setReady(true);
      })
      .catch(() => setReady(true));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      authenticated,
      ready,
      login: () => getKeycloak().login(),
      logout: () => getKeycloak().logout({ redirectUri: window.location.origin }),
    }),
    [authenticated, ready],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
