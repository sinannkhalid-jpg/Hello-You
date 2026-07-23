"""AI-style report generation.

This module produces a deterministic, structured OSINT report from the
data already gathered by the other modules. It does not call any external
LLM. The structure mirrors what a real analyst would write, so the
frontend can present a credible executive summary, risk assessment,
findings, and MITRE ATT&CK mapping suggestions.

The MITRE mappings are heuristic: certain indicators (open ports, weak
DNS, missing headers, expired cert) suggest corresponding techniques.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)

# Minimal MITRE ATT&CK technique references used by the mapping engine.
_MITRE: dict[str, dict[str, str]] = {
    "T1190":  {"name": "Exploit Public-Facing Application",   "tactic": "Initial Access"},
    "T1133":  {"name": "External Remote Services",             "tactic": "Initial Access"},
    "T1078":  {"name": "Valid Accounts",                       "tactic": "Defense Evasion / Persistence"},
    "T1595":  {"name": "Active Scanning",                      "tactic": "Reconnaissance"},
    "T1592":  {"name": "Gather Victim Host Information",       "tactic": "Reconnaissance"},
    "T1589":  {"name": "Gather Victim Identity Information",   "tactic": "Reconnaissance"},
    "T1590":  {"name": "Gather Victim Network Information",    "tactic": "Reconnaissance"},
    "T1591":  {"name": "Gather Victim Org Information",        "tactic": "Reconnaissance"},
    "T1583":  {"name": "Acquire Infrastructure",               "tactic": "Resource Development"},
    "T1566":  {"name": "Phishing",                             "tactic": "Initial Access"},
}


def _findings_for(kind: str, data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if kind == "domain":
        if data.get("ssl") and data["ssl"].get("days_remaining", 999) < 14:
            out.append(f"TLS certificate expires in {data['ssl']['days_remaining']} days.")
        if not data.get("dns", {}).get("dnssec"):
            out.append("DNSSEC is not enabled on the apex zone.")
        if data.get("dns", {}).get("mx"):
            out.append(f"Mail is routed to {len(data['dns']['mx'])} MX host(s).")
        if data.get("risk_score", 0) >= 50:
            out.append("Aggregate risk score is in the elevated band; review findings.")
        if data.get("technologies"):
            names = sorted({t['name'] for t in data["technologies"]})
            out.append(f"Detected public-facing technologies: {', '.join(names[:10])}.")
    elif kind == "ip":
        if data.get("open_ports"):
            out.append(f"Open ports observed on authorized target: {data['open_ports']}.")
        if data.get("abuse_reports"):
            out.append(f"Public abuse reports associated with this IP: {data['abuse_reports']}.")
        if data.get("geo", {}).get("country"):
            out.append(f"Geolocation suggests {data['geo']['country']} / {data['geo'].get('city', 'unknown city')}.")
    elif kind == "email":
        if not data.get("spf"):
            out.append("No SPF record published — spoofing risk.")
        if not data.get("dkim"):
            out.append("No DKIM record found for common selectors.")
        if not data.get("dmarc"):
            out.append("No DMARC policy — spoofed mail is unlikely to be rejected.")
        if data.get("breach_exposure"):
            out.append("Address appears in public breach corpora (HIBP).")
    elif kind == "username":
        if data.get("profiles"):
            out.append(f"Username present on {len(data['profiles'])} public platform(s).")
    return out


def _recommendations_for(kind: str, data: dict[str, Any]) -> list[str]:
    recs: list[str] = []
    if kind == "domain":
        if not data.get("dns", {}).get("dnssec"):
            recs.append("Enable DNSSEC to prevent cache-poisoning attacks.")
        if data.get("ssl") and data["ssl"].get("days_remaining", 999) < 30:
            recs.append("Renew TLS certificate before expiration.")
        if data.get("risk_score", 0) >= 50:
            recs.append("Run a deeper vulnerability scan and review exposed admin paths.")
    if kind == "email":
        if not data.get("dmarc"):
            recs.append("Publish a DMARC record (start with p=none, then move to quarantine/reject).")
        if not data.get("spf"):
            recs.append("Publish an SPF record listing authorized senders.")
        if not data.get("dkim"):
            recs.append("Configure DKIM signing on outbound mail.")
    if kind == "ip":
        if data.get("open_ports"):
            recs.append("Close any internet-exposed ports that are not strictly required.")
        if data.get("abuse_reports"):
            recs.append("Review AbuseIPDB reports; consider blocking or contacting ISP.")
    if not recs:
        recs.append("Continue periodic monitoring; re-investigate when configuration changes.")
    return recs


def _mitre_for(kind: str, data: dict[str, Any]) -> list[dict[str, str]]:
    mapped: list[str] = []
    if kind in ("domain", "ip"):
        mapped += ["T1590", "T1595"]
    if kind == "domain" and data.get("technologies"):
        mapped += ["T1592"]
    if kind == "ip" and data.get("open_ports"):
        mapped += ["T1190", "T1133"]
    if kind == "email" and data.get("breach_exposure"):
        mapped += ["T1078", "T1589"]
    if kind == "username" and data.get("profiles"):
        mapped += ["T1589", "T1591"]
    out: list[dict[str, str]] = []
    for tid in sorted(set(mapped)):
        m = _MITRE.get(tid)
        if m:
            out.append({"id": tid, "name": m["name"], "tactic": m["tactic"]})
    return out


def generate_report(target: str, kind: str, data: dict[str, Any]) -> dict[str, Any]:
    risk_score = int(data.get("risk_score", 0))
    threat_level = (
        "critical" if risk_score >= 75 else
        "high" if risk_score >= 50 else
        "medium" if risk_score >= 25 else "low"
    )
    findings = _findings_for(kind, data)
    recs = _recommendations_for(kind, data)
    mitre = _mitre_for(kind, data)
    infra: list[str] = []
    if kind == "domain":
        for h in (data.get("dns", {}).get("a") or []):
            infra.append(f"A record → {h}")
        for h in (data.get("dns", {}).get("aaaa") or []):
            infra.append(f"AAAA record → {h}")
        for mx in data.get("dns", {}).get("mx", []):
            infra.append(f"MX {mx['priority']} {mx['host']}")
        for ns in data.get("dns", {}).get("ns", []):
            infra.append(f"NS {ns}")
    elif kind == "ip":
        geo = data.get("geo", {})
        if geo.get("country"):
            infra.append(f"Geo: {geo.get('city')}, {geo.get('country')} ({geo.get('latitude')}, {geo.get('longitude')})")
        if data.get("isp"):
            infra.append(f"ISP: {data['isp']}")
        if data.get("asn"):
            infra.append(f"ASN: {data['asn']}")
        if data.get("reverse_dns"):
            infra.append(f"Reverse DNS: {data['reverse_dns']}")

    exec_summary = (
        f"Investigation of {kind} '{target}' produced a {threat_level} risk profile "
        f"(score {risk_score}/100). {len(findings)} finding(s) and {len(recs)} recommendation(s) "
        f"are recorded below. All data was gathered from publicly available sources."
    )

    risk_assessment = (
        f"The aggregate risk score is {risk_score} (level: {threat_level}). "
        "This is derived from publicly observable signals only and should be combined with "
        "internal context before any action is taken."
    )

    return {
        "target": target,
        "kind": kind,
        "threat_level": threat_level,
        "risk_score": risk_score,
        "executive_summary": exec_summary,
        "risk_assessment": risk_assessment,
        "findings": findings,
        "public_infrastructure": infra,
        "recommendations": recs,
        "mitre_attack": mitre,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
