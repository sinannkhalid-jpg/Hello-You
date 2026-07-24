"use client";
/**
 * Lightweight auth context (local JWT, with optional Supabase swap).
 * Keeps the access/refresh tokens in localStorage and exposes user + login/logout.
 */
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Auth, loadTokens, setTokens } from "./api";

type User = { id: string; email: string; full_name?: string | null; avatar_url?: string | null };

type AuthCtx = {
  user: User | null;
  ready: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name?: string) => Promise<void>;
  logout: () => Promise<void>;
  forgot: (email: string) => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);

  // Hydrate tokens + fetch me
  useEffect(() => {
    const { a, r } = loadTokens();
    setTokens(a, r);
    if (a) {
      Auth.me()
        .then((u) => setUser(u))
        .catch(() => {
          setTokens(null, null);
        })
        .finally(() => setReady(true));
    } else {
      setReady(true);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const r = await Auth.login({ email, password });
      setTokens(r.access_token, r.refresh_token);
      const u = await Auth.me();
      setUser(u);
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email: string, password: string, full_name?: string) => {
    setLoading(true);
    try {
      const r = await Auth.register({ email, password, full_name });
      setTokens(r.access_token, r.refresh_token);
      const u = await Auth.me();
      setUser(u);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try { await Auth.logout(); } catch { /* ignore */ }
    setTokens(null, null);
    setUser(null);
  }, []);

  const forgot = useCallback(async (email: string) => {
    await Auth.forgot(email);
  }, []);

  const value = useMemo(
    () => ({ user, ready, loading, login, register, logout, forgot }),
    [user, ready, loading, login, register, logout, forgot],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
