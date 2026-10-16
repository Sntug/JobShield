"""JobShield Backend API - Entry point tối thiểu cho R0."""

import logging
import os
from typing import Any, Dict
import uuid
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings


app = FastAPI(
    title="JobShield API",
    description="Backend API cho JobShield - Phân tích và đánh giá rủi ro tin tuyển dụng",
    version="0.1.0",
)

# CORS: Cho phép frontend (local dev và Vercel preview/production) kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn.error")
COMMIT_SHA = os.getenv("RENDER_GIT_COMMIT", os.getenv("GIT_COMMIT", "dev"))[:7]


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    """Truy vết request: sinh ID mới, trả header X-Request-ID và log an toàn."""
    request_id = uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Commit-SHA"] = COMMIT_SHA
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
