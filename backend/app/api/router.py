"""Main API router combining all route endpoints."""

from fastapi import APIRouter
from app.api.routes import analyses, verifications

api_router = APIRouter()
api_router.include_router(analyses.router)

api_router.include_router(verifications.router)
