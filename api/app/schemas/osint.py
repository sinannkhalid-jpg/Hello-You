"""Pydantic schemas for OSINT module responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Shared ----------
class InvestigationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    target: str
    title: Optional[str] = None
    risk_score: Optional[int] = None
    threat_level: Optional[str] = None
    is_favorite: bool
    created_at: datetime


class InvestigationDetail(InvestigationSummary):
    result: dict[str, Any]
    notes: Optional[str] = None
    duration_ms: Optional[int] = None


# ---------- Username ----------
class UsernameProfile(BaseModel):
    platform: str
    url: str
    exists: bool
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    followers: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)


class UsernameResult(BaseModel):
    username: str
    profiles: list[UsernameProfile]
    confidence: float
    timeline: list[dict[str, Any]] = []


# ---------- Email ----------
class EmailResult(BaseModel):
    email: str
    domain: str
    mx_records: list[dict[str, Any]] = []
    spf: Optional[str] = None
    dkim: Optional[str] = None
    dmarc: Optional[str] = None
    gravatar_url: Optional[str] = None
    breach_exposure: Optional[dict[str, Any]] = None
    risk_score: int = 0
    threat_level: str = "low"


# ---------- Phone ----------
class PhoneResult(BaseModel):
    number: str
    e164: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    carrier: Optional[str] = None
    timezone: Optional[str] = None
    number_type: Optional[str] = None
    flag_emoji: Optional[str] = None


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
    threat_level: str = "low"


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
    threat_level: str = "low"


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
    target: str
    kind: str
    context: dict[str, Any] = {}


class AIReport(BaseModel):
    target: str
    kind: str
    threat_level: str
    risk_score: int
    executive_summary: str
    risk_assessment: str
    findings: list[str]
    public_infrastructure: list[str]
    recommendations: list[str]
    mitre_attack: list[dict[str, Any]] = []
    generated_at: datetime
