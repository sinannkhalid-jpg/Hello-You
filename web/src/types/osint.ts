/** Loose shared types for OSINT results. Kept liberal to accept backend shape changes. */
export type InvestigationKind =
  | "username" | "email" | "phone" | "domain" | "ip" | "dns" | "whois" | "ssl" | "ct" | "subdomain" | "tech";

export type ThreatLevel = "low" | "medium" | "high" | "critical" | "unknown";

export interface InvestigationSummary {
  id: string;
  kind: string;
  target: string;
  title?: string | null;
  risk_score?: number | null;
  threat_level?: ThreatLevel | null;
  is_favorite: boolean;
  created_at: string;
}

export interface Investigation extends InvestigationSummary {
  result: any;
  notes?: string | null;
  duration_ms?: number | null;
}

export interface GraphNode { id: string; label: string; type: string; data?: any }
export interface GraphEdge { source: string; target: string; label?: string | null; type?: string | null }
