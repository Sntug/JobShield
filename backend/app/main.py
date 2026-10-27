"""JobShield Backend API - Entry point tối thiểu cho R0."""

import logging
import os
from typing import Any, Dict
import uuid
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.api.router import api_router
from app.api.verification_http import VerificationRequestGuard, verification_path, verification_error, verification_validation_error


app = FastAPI(
    title="JobShield API",
    description="Backend API cho JobShield - Phân tích và đánh giá rủi ro tin tuyển dụng",
    version="0.1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Sanitize lỗi 422: Không echo lại nội dung văn bản đầu vào để bảo vệ quyền riêng tư."""
    if verification_path(request.url.path):
        return verification_validation_error(request, exc)
    sanitized_errors = []
    for err in exc.errors():
        sanitized_errors.append({
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type"),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": sanitized_errors},
    )


# Gắn router API v1
app.include_router(api_router, prefix="/api/v1")

cors_origins_env = os.getenv("CORS_ORIGINS", "")
allow_origins = [
    origin.strip()
    for origin in cors_origins_env.split(",")
    if origin.strip()
] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://job-shield.vercel.app",
    "https://job-shield-virid.vercel.app",
]

app.add_middleware(VerificationRequestGuard)

# CORS: Chỉ cho phép các origin hợp lệ, không dùng credentials cookie, giới hạn methods/headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Guest-Session-Token", "X-Request-ID"],
    expose_headers=["Retry-After", "X-Request-ID", "X-Commit-SHA"],
)

logger = logging.getLogger("uvicorn.error")
COMMIT_SHA = os.getenv("RENDER_GIT_COMMIT", os.getenv("GIT_COMMIT", "dev"))[:7]


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    """Truy vết request: sinh ID mới, trả header X-Request-ID, no-store và log an toàn."""
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception as exc:
        if not verification_path(request.url.path):
            raise
        code = "SOURCE_STORE_UNAVAILABLE" if isinstance(exc, SQLAlchemyError) else "INTERNAL_ERROR"
        response = verification_error(request_id, 503 if isinstance(exc, SQLAlchemyError) else 500, code)
        origin = request.headers.get("origin")
        if origin in allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Commit-SHA"] = COMMIT_SHA

    # Mọi phản hồi thuộc endpoint cá nhân, auth và analyses đều không được lưu cache
    if (
        request.url.path == "/ready"
        or request.url.path.startswith("/api/v1/analyses")
        or request.url.path.startswith("/api/v1/auth")
        or request.url.path.startswith("/api/v1/users")
        or request.url.path.startswith("/api/v1/saved-analyses")
        or verification_path(request.url.path)
    ):
        response.headers["Cache-Control"] = "no-store"

    logger.info(
        "request_id=%s commit=%s method=%s path=%s status=%d",
        request_id,
        COMMIT_SHA,
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


@app.get("/")
def read_root() -> Dict[str, str]:
    """Endpoint gốc kiểm tra trạng thái hoạt động."""
    return {
        "message": "JobShield API đang hoạt động",
        "status": "ok",
        "version": "0.1.0",
        "commit": COMMIT_SHA,
    }


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    """Liveness probe: Kiểm tra process FastAPI đang sống."""
    return {"status": "healthy"}


@app.get("/ready")
def readiness(response: Response) -> Dict[str, Any]:
    """Readiness probe: kết nối, migration head và các cột model phải khả dụng."""
    try:
        settings = Settings()
    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "unconfigured",
            "message": "DATABASE_URL chưa được cấu hình",
        }

    from app.db.session import get_engine
    from app.services.readiness import check_readiness

    try:
        engine = get_engine()
        with engine.connect() as conn:
            schema_status = check_readiness(conn)
        return {
            "status": "ready",
            "database": "connected",
            **schema_status,
        }
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "unavailable",
            "schema": "unavailable",
            "message": "Không thể truy cập schema cần thiết của cơ sở dữ liệu",
        }
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "unavailable",
            "schema": "outdated_or_invalid",
            "message": "Schema chưa đúng phiên bản hoặc cấu hình database không hợp lệ",
        }
