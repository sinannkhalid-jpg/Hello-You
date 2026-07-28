"""Pydantic schemas for OSINT module responses.

Risk score semantics (consistent across the entire application):

  risk_score: 0-100  — higher = higher risk
  risk_level: "Low Risk" | "Guarded" | "Moderate" | "High Risk" | "Critical"

The legacy `threat_level` field is still accepted as input (with
short tokens) and emitted on the response (deprecated) for backward
compatibility. New code should use `risk_level` and `risk_score`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_risk_level(v: str | None) -> str:
    """Accept either the canonical names or the legacy short tokens
    and always return a canonical full name. This is used for the
    `risk_level` field on every schema that carries one."""
    if not v:
        return "Moderate"
    k = v.strip().lower()
    mapping = {
        "low":      "Low Risk",
        "guarded":  "Guarded",
        "medium":   "Moderate",
        "high":     "High Risk",
        "critical": "Critical",
    }
    if k in mapping:
        return mapping[k]
    for n in ("Low Risk", "Guarded", "Moderate", "High Risk", "Critical"):
        if n.lower() == k:
            return n
    return "Moderate"


# ---------- Shared ----------
class InvestigationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    target: str
    title: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    is_favorite: bool
    created_at: datetime

    @field_validator("risk_level", mode="before")
    @classmethod
    def _norm_risk_level(cls, v: Any) -> Any:
        return _normalize_risk_level(v) if isinstance(v, str) else v


class InvestigationDetail(InvestigationSummary):
    result: dict[str, Any]
    notes: Optional[str] = None
    duration_ms: Optional[int] = None


# ---------- Username ----------
class UsernameProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    platform: str
    url: str
    exists: bool
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    followers: Optional[int] = None
    verified: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    response_time_ms: int = 0


class UsernameResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    username: str
    profiles: list[UsernameProfile]
    confidence: float
    timeline: list[dict[str, Any]] = []
    count: int = 0
    blocked: list[dict[str, Any]] = []
    not_found: list[dict[str, Any]] = []
    providers_blocked: int = 0
    total_checked: int = 0


# ---------- Email ----------
class EmailResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    email: str
    domain: str
    provider: Optional[str] = None
    is_free_mail: bool = False
    is_disposable: bool = False
    is_role: bool = False
    mx_records: list[dict[str, Any]] = []
    spf: Optional[str] = None
    dkim: Optional[dict[str, Any]] = None
    dmarc: Optional[str] = None
    mta_sts: Optional[dict[str, Any]] = None
    tls: Optional[dict[str, Any]] = None
    bimi: Optional[str] = None
    dnssec: Optional[dict[str, Any]] = None
    nameservers: list[str] = []
    domain_age: Optional[dict[str, Any]] = None
    gravatar_url: Optional[str] = None
    gravatar_profile: Optional[dict[str, Any]] = None
    breach_exposure: Optional[dict[str, Any]] = None
    git_leaks: Optional[dict[str, Any]] = None
    leakcheck: Optional[dict[str, Any]] = None
    # Canonical risk fields (new)
    risk_score: int = 0
    risk_level: str = "Moderate"
    risk: Optional[dict[str, Any]] = None
    # Back-compat: legacy alias
    reputation: Optional[dict[str, Any]] = None
    threat_level: str = "moderate"  # legacy short token, derived from risk_level
    providers: dict[str, Any] = {}
    duration_ms: int = 0

    @field_validator("risk_level", mode="before")
    @classmethod
    def _norm_risk_level(cls, v: Any) -> Any:
        return _normalize_risk_level(v) if isinstance(v, str) else v

    @field_validator("threat_level", mode="before")
    @classmethod
    def _norm_threat(cls, v: Any) -> Any:
        # Keep the short token form on the legacy field
        if not v:
            return "moderate"
        k = v.strip().lower()
        if k in ("low", "guarded", "medium", "high", "critical"):
            return k
        # If a canonical name is passed, map to short token
        return {
            "Low Risk":  "low",
            "Guarded":   "guarded",
            "Moderate":  "medium",
            "High Risk": "high",
            "Critical":  "critical",
        }.get(v, "moderate")


# ---------- Phone ----------
class PhoneResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    number: str
    e164: Optional[str] = ""
    valid: bool = False
    country: Optional[str] = None
    country_name: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    carrier: Optional[str] = None
    timezone: Optional[str] = None
    timezones: list[str] = []
    number_type: Optional[str] = None
    number_type_name: Optional[str] = None
    flag_emoji: Optional[str] = None
    is_mobile: bool = False
    is_fixed_line: bool = False
    is_toll_free: bool = False
    is_voip: bool = False
    is_premium_rate: bool = False
    formats: dict[str, Any] = {}
    messaging: dict[str, Any] = {}
    risk: dict[str, Any] = {}            # NEW canonical — spam/fraud scoring as risk
    reputation: dict[str, Any] = {}       # legacy alias for risk
    portability: dict[str, Any] = {}
    business_association: Optional[Any] = None
    confidence: float = 0.0
    data_sources: list[str] = []


# ---------- Domain ----------
class DNSRecords(BaseModel):
    a: list[str] = []
    aaaa: list[str] = []
    mx: list[dict[str, Any]] = []
    ns: list[str] = []
    txt: list[str] = []
    cname: list[str] = []
    soa: Optional[dict[str, Any]] = None
    caa: list[dict[str, Any]] = []
    ptr: list[str] = []
    dnssec: bool = False


class SSLInfo(BaseModel):
    issuer: Optional[str] = None
    subject: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    days_remaining: Optional[int] = None
    fingerprint_sha256: Optional[str] = None
    public_key_algorithm: Optional[str] = None
    signature_algorithm: Optional[str] = None
    chain_valid: Optional[bool] = None
    san: list[str] = []


class WHOISInfo(BaseModel):
    registrar: Optional[str] = None
    registrant: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    nameservers: list[str] = []
    statuses: list[str] = []
    source: str = "rdap"
    raw: dict[str, Any] = {}


class Technology(BaseModel):
    name: str
    category: str
    confidence: float = 0.0
    evidence: Optional[str] = None


class DomainResult(BaseModel):
    domain: str
    dns: DNSRecords
    ssl: Optional[SSLInfo] = None
    whois: Optional[WHOISInfo] = None
    technologies: list[Technology] = []
    headers: dict[str, str] = {}
    cdn: Optional[str] = None
    hosting: Optional[str] = None
    risk_score: int = 0
    risk_level: str = "Moderate"
    threat_level: str = "moderate"  # legacy short token

    @field_validator("risk_level", mode="before")
    @classmethod
    def _norm_risk_level(cls, v: Any) -> Any:
        return _normalize_risk_level(v) if isinstance(v, str) else v


# ---------- IP ----------
class GeoInfo(BaseModel):
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None


class IPResult(BaseModel):
    ip: str
    reverse_dns: Optional[str] = None
    geo: GeoInfo
    isp: Optional[str] = None
    asn: Optional[str] = None
    asn_org: Optional[str] = None
    open_ports: list[int] = []  # only when authorized target
    threat_intel: dict[str, Any] = {}
    abuse_reports: Optional[int] = None
    risk_score: int = 0
    risk_level: str = "Moderate"
    threat_level: str = "moderate"  # legacy short token

    @field_validator("risk_level", mode="before")
    @classmethod
    def _norm_risk_level(cls, v: Any) -> Any:
        return _normalize_risk_level(v) if isinstance(v, str) else v


# ---------- Subdomains ----------
class SubdomainResult(BaseModel):
    domain: str
    subdomains: list[str]
    sources: list[str] = []


# ---------- Relationship graph ----------
class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # person|email|phone|username|domain|ip|website|company
    data: dict[str, Any] = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None
    type: Optional[str] = None


class GraphResult(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------- AI report ----------
class AIReportRequest(BaseModel):
    investigation_id: Optional[str] = None
    target: str = Field(min_length=1, max_length=512)
    kind: Literal["domain", "ip", "email", "username", "url"]
    context: dict[str, Any] = {}


class AIReport(BaseModel):
    target: str
    kind: str
    risk_level: str = "Moderate"
    risk_score: int = 0
    threat_level: str = "moderate"  # legacy short token
    executive_summary: str
    risk_assessment: str
    findings: list[str]
    public_infrastructure: list[str]
    recommendations: list[str]
    mitre_attack: list[dict[str, Any]] = []
    generated_at: datetime

    @field_validator("risk_level", mode="before")
    @classmethod
    def _norm_risk_level(cls, v: Any) -> Any:
        return _normalize_risk_level(v) if isinstance(v, str) else v
