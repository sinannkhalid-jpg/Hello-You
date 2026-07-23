"""Phone number intelligence.

Uses Google's `libphonenumber` for parsing/validation (offline, no API).
We never call any carrier/private-lookup service. We only expose
public metadata: country, region, carrier (best-effort via libphonenumber
metadata), timezone, number type.
"""
from __future__ import annotations

import phonenumbers  # type: ignore
from phonenumbers import carrier, geocoder, timezone as ph_tz  # type: ignore

from app.core.logging import get_logger

log = get_logger(__name__)

_FLAG = {
    "US": "🇺🇸", "GB": "🇬🇧", "IN": "🇮🇳", "DE": "🇩🇪", "FR": "🇫🇷", "JP": "🇯🇵",
    "CN": "🇨🇳", "RU": "🇷🇺", "BR": "🇧🇷", "CA": "🇨🇦", "AU": "🇦🇺", "IT": "🇮🇹",
    "ES": "🇪🇸", "MX": "🇲🇽", "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮",
    "DK": "🇩🇰", "CH": "🇨🇭", "AT": "🇦🇹", "BE": "🇧🇪", "PL": "🇵🇱", "TR": "🇹🇷",
    "AE": "🇦🇪", "SA": "🇸🇦", "IL": "🇮🇱", "SG": "🇸🇬", "KR": "🇰🇷", "NZ": "🇳🇿",
    "ZA": "🇿🇦", "EG": "🇪🇬", "NG": "🇳🇬", "AR": "🇦🇷", "CL": "🇨🇱", "CO": "🇨🇴",
}


def lookup(number: str) -> dict:
    try:
        pn = phonenumbers.parse(number, None)
    except phonenumbers.NumberParseException:
        # Try with default region
        try:
            pn = phonenumbers.parse(number, "US")
        except phonenumbers.NumberParseException as e:
            log.info("phone parse failed: %s", e)
            return {
                "number": number, "e164": None, "valid": False,
                "country": None, "country_code": None, "region": None,
                "carrier": None, "timezone": None, "number_type": None,
                "flag_emoji": None,
            }

    cc = phonenumbers.region_code_for_number(pn)
    desc = geocoder.description_for_number(pn, "en")
    tz = ph_tz.time_zones_for_number(pn)
    ntype = phonenumbers.number_type(pn)
    ntype_name = {
        0: "FIXED_LINE", 1: "MOBILE", 2: "FIXED_LINE_OR_MOBILE",
        3: "TOLL_FREE", 4: "PREMIUM_RATE", 5: "SHARED_COST", 6: "VOIP",
        7: "PERSONAL_NUMBER", 8: "PAGER", 9: "UAN", 10: "VOICEMAIL",
        -1: "UNKNOWN",
    }.get(int(ntype), "UNKNOWN")

    return {
        "number": number,
        "e164": phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164),
        "valid": phonenumbers.is_valid_number(pn),
        "country": cc,
        "country_code": str(pn.country_code),
        "region": desc or None,
        "carrier": carrier.name_for_number(pn, "en") or None,
        "timezone": tz[0] if tz else None,
        "number_type": ntype_name,
        "flag_emoji": _FLAG.get(cc or "", "🌐"),
    }
