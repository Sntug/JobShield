"""Main API router combining all route endpoints."""

from fastapi import APIRouter
from app.api.routes import analyses, auth, saved_analyses, users, verifications

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(analyses.router)
api_router.include_router(saved_analyses.router)
api_router.include_router(verifications.router)
