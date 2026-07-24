"""
JSON-safe serializer for investigation results.

SQLite's JSON column can't handle datetimes or other non-JSON types by
default. Pydantic's `model_dump(mode="json")` handles most of our
Pydantic models, but free-form provider results (WHOIS RDAP, etc.)
may contain datetime objects. This helper recursively converts any
non-JSON-safe value into a string.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any


def to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):  # Pydantic model
        try:
            return to_jsonable(value.model_dump(mode="json"))
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return to_jsonable(vars(value))
    return str(value)
