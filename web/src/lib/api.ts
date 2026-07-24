/**
 * Browser API client for the Hello You FastAPI backend.
 * Handles auth tokens, base URL, JSON encoding, and typed errors.
 */
const BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  data: any;
  constructor(status: number, message: string, data: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(a: string | null, r: string | null) {
  accessToken = a;
  refreshToken = r;
  if (typeof window !== "undefined") {
    if (a) localStorage.setItem("osint_access", a); else localStorage.removeItem("osint_access");
    if (r) localStorage.setItem("osint_refresh", r); else localStorage.removeItem("osint_refresh");
  }
}
export function loadTokens() {
  if (typeof window === "undefined") return { a: null, r: null };
  return {
    a: localStorage.getItem("osint_access"),
    r: localStorage.getItem("osint_refresh"),
  };
}

export function getAccessToken() {
  if (accessToken) return accessToken;
  if (typeof window !== "undefined") return localStorage.getItem("osint_access");
  return null;
}

type Options = RequestInit & { json?: any; query?: Record<string, any> };

export async function api<T = any>(path: string, opts: Options = {}): Promise<T> {
  const url = new URL(BASE + path);
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v != null && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(opts.headers as Record<string, string>),
  };
  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  } else {
    body = opts.body as BodyInit | undefined;
  }
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(url.toString(), { ...opts, headers, body, cache: "no-store" });
  } catch (e: any) {
    throw new ApiError(0, `Network error: ${e?.message || e}`, null);
  }

  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    // Auto-refresh once on 401
    if (res.status === 401 && refreshToken && path !== "/api/v1/auth/refresh" && path !== "/api/v1/auth/login") {
      const r = await tryRefresh();
      if (r) {
        return api<T>(path, opts);
      }
    }
    const detail = (data && (data.detail || data.message)) || res.statusText;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail), data);
  }
  return data as T;
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      setTokens(null, null);
      return false;
    }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    setTokens(null, null);
    return false;
  }
}

// -- Typed helpers (kept loose to avoid duplicate-of-backend drift) --
export const Auth = {
  register: (body: { email: string; password: string; full_name?: string }) =>
    api<{ access_token: string; refresh_token: string }>("/api/v1/auth/register", { method: "POST", json: body }),
  login: (body: { email: string; password: string }) =>
    api<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", { method: "POST", json: body }),
  refresh: (token: string) =>
    api<{ access_token: string; refresh_token: string }>("/api/v1/auth/refresh", { method: "POST", json: { refresh_token: token } }),
  forgot: (email: string) =>
    api<{ message: string }>("/api/v1/auth/forgot-password", { method: "POST", json: { email } }),
  me: () => api<any>("/api/v1/auth/me"),
  logout: () => api<{ message: string }>("/api/v1/auth/logout", { method: "POST" }),
};

export const Dashboard = {
  get: () => api<any>("/api/v1/dashboard"),
};

export const Osint = {
  username: (u: string) => api<any>(`/api/v1/username/${encodeURIComponent(u)}`),
  email:    (e: string) => api<any>(`/api/v1/email/${encodeURIComponent(e)}`),
  phone:    (n: string) => api<any>(`/api/v1/phone/${encodeURIComponent(n)}`),
  domain:   (d: string) => api<any>(`/api/v1/domain/${encodeURIComponent(d)}`),
  dns:      (d: string) => api<any>(`/api/v1/dns/${encodeURIComponent(d)}`),
  whois:    (d: string) => api<any>(`/api/v1/whois/${encodeURIComponent(d)}`),
  ssl:      (d: string) => api<any>(`/api/v1/ssl/${encodeURIComponent(d)}`),
  ct:       (d: string, limit = 50) => api<any[]>(`/api/v1/ct/${encodeURIComponent(d)}`, { query: { limit } }),
  subdomains: (d: string) => api<any>(`/api/v1/subdomains/${encodeURIComponent(d)}`),
  tech:     (d: string) => api<any[]>(`/api/v1/tech/${encodeURIComponent(d)}`),
  ip:       (ip: string) => api<any>(`/api/v1/ip/${encodeURIComponent(ip)}`),
  ipPortScan: (ip: string, authorized = true) =>
    api<any>(`/api/v1/ip/${encodeURIComponent(ip)}/port-scan`, { method: "POST", json: { authorized } }),
  graphFromInvestigation: (id: string) => api<any>(`/api/v1/graph/investigation/${id}`),
  graphFromData: (kind: string, target: string, data: any) =>
    api<any>("/api/v1/graph/from-data", { method: "POST", json: { kind, target, data } }),
};

export const Investigations = {
  list: (params: { kind?: string; favorite?: boolean; search?: string; limit?: number; offset?: number } = {}) =>
    api<any[]>("/api/v1/investigations", { query: params }),
  get: (id: string) => api<any>(`/api/v1/investigations/${id}`),
  favorite: (id: string) => api<any>(`/api/v1/investigations/${id}/favorite`, { method: "POST" }),
  delete: (id: string) => api<{ deleted: boolean }>(`/api/v1/investigations/${id}`, { method: "DELETE" }),
};

export const Reports = {
  generate: (body: { target: string; kind: string; context?: any; investigation_id?: string }) =>
    api<any>("/api/v1/reports/generate", { method: "POST", json: body }),
  exportUrl: (invId: string, fmt: "pdf" | "csv" | "json") =>
    `${BASE}/api/v1/reports/export/${invId}?fmt=${fmt}`,
};

export const Settings = {
  prefs: () => api<any>("/api/v1/settings/preferences"),
  updatePrefs: (p: any) => api<any>("/api/v1/settings/preferences", { method: "PUT", json: p }),
  export: () => api<any>("/api/v1/settings/export"),
  deleteAccount: () => api<{ deleted: boolean }>("/api/v1/settings/account", { method: "DELETE" }),
  info: () => api<any>("/api/v1/settings/info"),
};
