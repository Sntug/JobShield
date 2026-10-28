"""Main API router combining all route endpoints."""

from fastapi import APIRouter
from app.api.routes import (
    admin,
    analyses,
    auth,
    extraction,
    reports,
    saved_analyses,
    users,
    verifications,
    warnings,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(analyses.router)
api_router.include_router(saved_analyses.router)
api_router.include_router(verifications.router)
api_router.include_router(extraction.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(warnings.router)
