"""
Backwards-compat shim: ``from app.services.providers import ...`` continues to
work. The real implementation lives in
``app/services/providers/`` as a package.
"""
from app.services.providers import base, cache, ratelimit, types  # noqa: F401
