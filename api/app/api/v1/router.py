"""API v1 router aggregator."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    dashboard,
    domain,
    email,
    graph,
    intel,
    investigations,
    ip,
    phone,
    reports,
    settings,
    username,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(username.router)
api_router.include_router(email.router)
api_router.include_router(phone.router)
api_router.include_router(domain.router)
api_router.include_router(domain.dns_router)
api_router.include_router(domain.whois_router)
api_router.include_router(domain.ssl_router)
api_router.include_router(domain.ct_router)
api_router.include_router(domain.sub_router)
api_router.include_router(domain.tech_router)
api_router.include_router(ip.router)
api_router.include_router(graph.router)
api_router.include_router(reports.router)
api_router.include_router(investigations.router)
api_router.include_router(settings.router)
# New: provider-orchestrated intel endpoint
api_router.include_router(intel.router)
