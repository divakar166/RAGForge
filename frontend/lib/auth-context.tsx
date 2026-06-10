"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { User, LoginBody, RegisterBody } from "./types";
import { api } from "./api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (body: LoginBody) => Promise<void>;
  register: (body: RegisterBody) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.getMe();
      setUser(me);
      setError(null);
    } catch {
      setUser(null);
      api.clearTokens();
    }
  }, []);

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
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  }, []);

  const register = useCallback(async (body: RegisterBody) => {
    setError(null);
    try {
      await api.register(body);
      await api.login({ email: body.email, password: body.password });
      const me = await api.getMe();
      setUser(me);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, error, login, register, logout, refreshUser }}
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
