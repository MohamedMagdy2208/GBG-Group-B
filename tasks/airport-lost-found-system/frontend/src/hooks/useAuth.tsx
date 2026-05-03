import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, clearAuthTokens, setAuthTokens } from "../api/client";
import type { Role, User } from "../types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string, phone?: string) => Promise<User>;
  logout: () => Promise<void>;
  hasRole: (roles: Role[]) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    const handleExpired = () => {
      setUser(null);
      setSessionExpired(true);
    };
    window.addEventListener("auth:expired", handleExpired);
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return () => window.removeEventListener("auth:expired", handleExpired);
    }
    api
      .get<User>("/auth/me")
      .then((response) => setUser(response.data))
      .catch(() => clearAuthTokens())
      .finally(() => setLoading(false));
    return () => window.removeEventListener("auth:expired", handleExpired);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      sessionExpired,
      async login(email, password) {
        const response = await api.post("/auth/login", { email, password });
        setAuthTokens(response.data.access_token, response.data.refresh_token, response.data.expires_in_seconds);
        setSessionExpired(false);
        setUser(response.data.user);
        return response.data.user;
      },
      async register(name, email, password, phone) {
        const response = await api.post("/auth/register", { name, email, password, phone });
        setAuthTokens(response.data.access_token, response.data.refresh_token, response.data.expires_in_seconds);
        setSessionExpired(false);
        setUser(response.data.user);
        return response.data.user;
      },
      async logout() {
        const refreshToken = localStorage.getItem("refresh_token");
        try {
          await api.post("/auth/logout", { refresh_token: refreshToken });
        } catch {
          // Session cleanup should still complete if the API is already unavailable.
        }
        clearAuthTokens();
        setSessionExpired(false);
        setUser(null);
      },
      hasRole(roles) {
        return Boolean(user && roles.includes(user.role));
      },
    }),
    [loading, sessionExpired, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
