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


app = FastAPI(
    title="JobShield API",
    description="Backend API cho JobShield - Phân tích và đánh giá rủi ro tin tuyển dụng",
    version="0.1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Sanitize lỗi 422: Không echo lại nội dung văn bản đầu vào để bảo vệ quyền riêng tư."""
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

# CORS: Chỉ cho phép các origin hợp lệ, không dùng credentials cookie, giới hạn methods/headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Guest-Session-Token", "X-Request-ID"],
    expose_headers=["Retry-After", "X-Request-ID", "X-Commit-SHA"],
)

logger = logging.getLogger("uvicorn.error")
COMMIT_SHA = os.getenv("RENDER_GIT_COMMIT", os.getenv("GIT_COMMIT", "dev"))[:7]


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    """Truy vết request: sinh ID mới, trả header X-Request-ID, no-store và log an toàn."""
    request_id = uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Commit-SHA"] = COMMIT_SHA

    # Mọi phản hồi thuộc endpoint analyses (kể cả lỗi 401, 404, 422) đều không được lưu cache
    if request.url.path.startswith("/api/v1/analyses"):
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
    """Readiness probe: Kiểm tra kết nối tới cơ sở dữ liệu PostgreSQL."""
    try:
        settings = Settings()
    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "unconfigured",
            "message": "DATABASE_URL chưa được cấu hình",
        }

    from sqlalchemy import create_engine

    try:
        engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
        }
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "disconnected",
            "message": "Không thể kết nối cơ sở dữ liệu",
        }
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "error",
            "message": "Lỗi kết nối kiểm tra database",
        }
