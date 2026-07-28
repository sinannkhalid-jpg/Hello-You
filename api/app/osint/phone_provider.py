"""Phone number intelligence.

Public signals we collect:
  • libphonenumber metadata: country, region, carrier (best-effort),
    timezone, number type, validity, E.164 format
  • WhatsApp presence: PUBLIC note — wa.me/<n> always redirects to
    api.whatsapp.com/send regardless of registration. We cannot
    detect WhatsApp presence without authentication. We report this
    explicitly.
  • Telegram presence: t.me/+<e164> returns a profile if the user has
    linked their phone to a public username. The page is a real
    profile (with tgme_page_title) if linked, or a generic page if not.
  • Signal presence: Signal does not provide a public lookup API.
    Reported as blocked with reason 'no_public_api'.
  • Reputation: spam/fraud scoring from public sources (none currently;
    reported as 'no_data')
  • Number portability: tracked via the original-network hint in the
    libphonenumber metadata (libphonenumber's carrier.name_for_number
    returns the *original* carrier at number allocation, not the current
    one — useful for portability hints)

We never call any carrier/private-lookup service. We only expose
public metadata: country, region, carrier (best-effort via
libphonenumber metadata), timezone, number type.
"""
from __future__ import annotations

from typing import Any

import phonenumbers  # type: ignore
import httpx
from phonenumbers import carrier, geocoder, timezone as ph_tz  # type: ignore

from app.core.logging import get_logger

log = get_logger(__name__)

# Country code → country name (short, common subset)
_COUNTRY_NAMES = {
    "US": "United States", "GB": "United Kingdom", "IN": "India",
    "DE": "Germany", "FR": "France", "JP": "Japan", "CN": "China",
    "RU": "Russia", "BR": "Brazil", "CA": "Canada", "AU": "Australia",
    "IT": "Italy", "ES": "Spain", "MX": "Mexico", "NL": "Netherlands",
    "SE": "Sweden", "NO": "Norway", "FI": "Finland", "DK": "Denmark",
    "CH": "Switzerland", "AT": "Austria", "BE": "Belgium", "PL": "Poland",
    "TR": "Turkey", "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "IL": "Israel", "SG": "Singapore", "KR": "South Korea", "NZ": "New Zealand",
    "ZA": "South Africa", "EG": "Egypt", "NG": "Nigeria", "AR": "Argentina",
    "CL": "Chile", "CO": "Colombia", "PT": "Portugal", "IE": "Ireland",
    "HK": "Hong Kong", "TW": "Taiwan", "TH": "Thailand", "MY": "Malaysia",
    "PH": "Philippines", "ID": "Indonesia", "VN": "Vietnam", "PK": "Pakistan",
    "BD": "Bangladesh", "LK": "Sri Lanka", "NP": "Nepal", "KE": "Kenya",
}

_FLAG = {
    "US": "🇺🇸", "GB": "🇬🇧", "IN": "🇮🇳", "DE": "🇩🇪", "FR": "🇫🇷", "JP": "🇯🇶",
    "CN": "🇨🇳", "RU": "🇷🇺", "BR": "🇧🇷", "CA": "🇨🇦", "AU": "🇦🇺", "IT": "🇮🇹",
    "ES": "🇪🇸", "MX": "🇲🇽", "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮",
    "DK": "🇩🇰", "CH": "🇨🇭", "AT": "🇦🇹", "BE": "🇧🇪", "PL": "🇵🇱", "TR": "🇹🇷",
    "AE": "🇦🇪", "SA": "🇸🇦", "IL": "🇮🇱", "SG": "🇸🇬", "KR": "🇰🇷", "NZ": "🇳🇿",
    "ZA": "🇿🇦", "EG": "🇪🇬", "NG": "🇳🇬", "AR": "🇦🇷", "CL": "🇨🇱", "CO": "🇨🇴",
    "PT": "🇵🇹", "IE": "🇮🇪", "HK": "🇭🇰", "TW": "🇹🇼", "TH": "🇹🇭", "MY": "🇲🇾",
    "PH": "🇵🇭", "ID": "🇮🇩", "VN": "🇻🇳", "PK": "🇵🇰", "BD": "🇧🇩", "LK": "🇱🇰",
    "NP": "🇳🇵", "KE": "🇰🇪",
}

_NUMBER_TYPE_NAMES = {
    0: "FIXED_LINE", 1: "MOBILE", 2: "FIXED_LINE_OR_MOBILE",
    3: "TOLL_FREE", 4: "PREMIUM_RATE", 5: "SHARED_COST", 6: "VOIP",
    7: "PERSONAL_NUMBER", 8: "PAGER", 9: "UAN", 10: "VOICEMAIL",
    -1: "UNKNOWN",
}


def _empty_result(number: str) -> dict[str, Any]:
    """Standard empty result for unparseable numbers."""
    return {
        "number": number,
        "e164": "",
        "valid": False,
        "country": None,
        "country_name": None,
        "country_code": None,
        "region": None,
        "carrier": None,
        "timezone": None,
        "timezones": [],
        "number_type": None,
        "number_type_name": None,
        "flag_emoji": None,
        "is_mobile": False,
        "is_fixed_line": False,
        "is_toll_free": False,
        "is_voip": False,
        "is_premium_rate": False,
        "reason": "parse_failed",
        "messaging": {
            "whatsapp": {
                "available": None,
                "reason": "no_public_api",
                "detail": ("WhatsApp does not expose a public lookup API. "
                           "wa.me/<n> always redirects to the chat send endpoint "
                           "regardless of whether the number is registered."),
            },
            "telegram": {
                "available": None,
                "reason": "not_checked",
            },
            "signal": {
                "available": None,
                "reason": "no_public_api",
                "detail": "Signal does not provide a public lookup API.",
            },
        },
        # Canonical: `risk` carries spam/fraud scoring (higher = more risky).
        "risk": {
            "spam_score": None,
            "fraud_score": None,
            "reason": "no_data",
            "detail": "No public reputation source is configured.",
        },
        # Legacy alias kept for back-compat with older clients.
        "reputation": {
            "spam_score": None,
            "fraud_score": None,
            "reason": "no_data",
            "detail": "No public reputation source is configured.",
        },
        "portability": {
            "original_carrier": None,
            "current_carrier_known": False,
            "reason": "portability_data_not_available",
        },
        "business_association": None,
        "confidence": 0.0,
        "data_sources": ["libphonenumber"],
    }


def lookup(number: str) -> dict:
    """Synchronous core lookup. Uses libphonenumber metadata only."""
    try:
        pn = phonenumbers.parse(number, None)
    except phonenumbers.NumberParseException:
        try:
            pn = phonenumbers.parse(number, "US")
        except phonenumbers.NumberParseException as e:
            log.info("phone parse failed: %s", e)
            return _empty_result(number)

    cc = phonenumbers.region_code_for_number(pn)
    cc_num = pn.country_code
    desc = geocoder.description_for_number(pn, "en")
    tz_list = ph_tz.time_zones_for_number(pn) or ()
    ntype = phonenumbers.number_type(pn)
    ntype_name = _NUMBER_TYPE_NAMES.get(int(ntype), "UNKNOWN")
    is_valid = phonenumbers.is_valid_number(pn)
    is_mobile = ntype == phonenumbers.PhoneNumberType.MOBILE
    is_fixed = ntype == phonenumbers.PhoneNumberType.FIXED_LINE
    is_toll_free = ntype == phonenumbers.PhoneNumberType.TOLL_FREE
    is_voip = ntype == phonenumbers.PhoneNumberType.VOIP
    is_premium = ntype == phonenumbers.PhoneNumberType.PREMIUM_RATE
    carrier_name = carrier.name_for_number(pn, "en") or None

    e164 = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)
    intl = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    national = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.NATIONAL)

    return {
        "number": number,
        "e164": e164,
        "valid": is_valid,
        "country": cc,
        "country_name": _COUNTRY_NAMES.get(cc or "", cc or None),
        "country_code": str(cc_num) if cc_num is not None else None,
        "region": desc or None,
        "carrier": carrier_name,
        "timezone": tz_list[0] if tz_list else None,
        "timezones": list(tz_list),
        "number_type": str(ntype),
        "number_type_name": ntype_name,
        "flag_emoji": _FLAG.get(cc or "", "🌐"),
        "is_mobile": is_mobile,
        "is_fixed_line": is_fixed,
        "is_toll_free": is_toll_free,
        "is_voip": is_voip,
        "is_premium_rate": is_premium,
        "formats": {
            "e164": e164,
            "international": intl,
            "national": national,
        },
        # Populated by async enrichment
        "messaging": {
            "whatsapp": {
                "available": None,
                "reason": "no_public_api",
                "detail": ("WhatsApp does not expose a public lookup API. "
                           "wa.me/<n> always redirects to the chat send endpoint "
                           "regardless of whether the number is registered."),
            },
            "telegram": {
                "available": None,
                "reason": "not_checked",
            },
            "signal": {
                "available": None,
                "reason": "no_public_api",
                "detail": "Signal does not provide a public lookup API.",
            },
        },
        # Canonical: `risk` carries spam/fraud scoring (higher = more risky).
        "risk": {
            "spam_score": None,
            "fraud_score": None,
            "reason": "no_data",
            "detail": "No public reputation source is configured.",
        },
        # Legacy alias.
        "reputation": {
            "spam_score": None,
            "fraud_score": None,
            "reason": "no_data",
            "detail": "No public reputation source is configured.",
        },
        "portability": {
            "original_carrier": carrier_name,
            "current_carrier_known": False,
            "reason": ("libphonenumber's carrier.name_for_number returns the "
                       "carrier at number allocation, not the current one. "
                       "Real portability lookups require carrier-grade APIs."),
        },
        "business_association": None,
        "confidence": 0.85,  # libphonenumber metadata is reliable
        "data_sources": ["libphonenumber"],
    }


async def async_enrichment(base: dict) -> dict:
    """Add async-only signals: Telegram public link, etc.

    Returns the same dict with the additional fields filled in.
    Never raises — any failure is silently absorbed and the field
    is set to None with a `reason` explaining why.
    """
    e164 = base.get("e164") or ""
    if not e164 or not base.get("valid"):
        return base
    digits = e164.lstrip("+")
    if not digits:
        return base

    # Telegram: t.me/+<digits-without-+>
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=6.0,
        ) as client:
            r = await client.get(f"https://t.me/+{digits}")
        if r is not None and r.status_code == 200:
            text = r.text or ""
            # Real linked numbers produce a profile page with tgme_page_title
            if "tgme_page_title" in text and "tgme_page_action" in text:
                import re
                m = re.search(r'<title>([^<]+)</title>', text)
                title = m.group(1).strip() if m else None
                base["messaging"]["telegram"] = {
                    "available": True,
                    "reason": None,
                    "profile_url": f"https://t.me/+{digits}",
                    "title": title,
                }
            else:
                base["messaging"]["telegram"] = {
                    "available": False,
                    "reason": "not_linked",
                    "detail": ("The number is not linked to a public Telegram "
                               "account. Users can hide their phone number in "
                               "Telegram's privacy settings."),
                }
        else:
            base["messaging"]["telegram"] = {
                "available": None,
                "reason": "lookup_failed",
                "status": r.status_code if r else None,
            }
    except Exception as e:  # noqa: BLE001
        log.debug("telegram check failed: %s", e)
        base["messaging"]["telegram"] = {
            "available": None,
            "reason": "request_failed",
        }

    # Update confidence based on what we could check
    if base["messaging"]["telegram"].get("available") is True:
        base["confidence"] = min(0.99, base["confidence"] + 0.1)
        if "telegram" not in base.get("data_sources", []):
            base.setdefault("data_sources", []).append("telegram_public_link")

    return base
