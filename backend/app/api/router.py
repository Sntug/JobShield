"""Main API router combining all route endpoints."""

from fastapi import APIRouter
from app.api.routes import analyses

api_router = APIRouter()
api_router.include_router(analyses.router)
