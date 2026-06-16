"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { User, LoginBody, RegisterBody, RegisterResponse, OrgInfo } from "./types";
import { api } from "./api";

interface AuthContextValue {
  user: User | null;
  activeOrg: OrgInfo | null;
  loading: boolean;
  error: string | null;
  login: (body: LoginBody) => Promise<void>;
  register: (body: RegisterBody) => Promise<RegisterResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  switchOrg: (orgId: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [activeOrg, setActiveOrg] = useState<OrgInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resolveOrg = useCallback((me: User) => {
    const savedId = api.orgId;
    if (savedId) {
      const match = me.organizations.find((o) => o.id === savedId);
      if (match) {
        setActiveOrg(match);
        return;
      }
    }
    const first = me.organizations[0];
    if (first) {
      api.orgId = first.id;
      setActiveOrg(first);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.getMe();
      setUser(me);
      resolveOrg(me);
      setError(null);
    } catch {
      setUser(null);
      setActiveOrg(null);
      api.clearTokens();
    }
  }, [resolveOrg]);

  useEffect(() => {
    if (api.getAccessToken()) {
      refreshUser().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [refreshUser]);

  const login = useCallback(async (body: LoginBody) => {
    setError(null);
    try {
      await api.login(body);
      const me = await api.getMe();
      setUser(me);
      resolveOrg(me);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  }, [resolveOrg]);

  const register = useCallback(async (body: RegisterBody) => {
    setError(null);
    try {
      const resp = await api.register(body);
      api.setTokens(resp);
      api.orgId = resp.org_id;
      setActiveOrg({
        id: resp.org_id,
        name: resp.org_name,
        slug: body.org_slug,
        role: "owner",
      });
      const me = await api.getMe();
      setUser(me);
      return resp;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
      throw err;
    }
  }, []);

  const switchOrg = useCallback(async (orgId: string) => {
    setError(null);
    try {
      const tokens = await api.selectOrg(orgId);
      api.setTokens(tokens);
      api.orgId = orgId;
      const me = await api.getMe();
      setUser(me);
      const match = me.organizations.find((o) => o.id === orgId);
      if (match) setActiveOrg(match);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to switch org";
      setError(message);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
    setActiveOrg(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, activeOrg, loading, error, login, register, logout, refreshUser, switchOrg }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
