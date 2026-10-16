"""JobShield Backend API - Entry point tối thiểu cho R0."""

from typing import Any, Dict
from fastapi import FastAPI, Response, status
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


@app.get("/")
def read_root() -> Dict[str, str]:
    """Endpoint gốc kiểm tra trạng thái hoạt động."""
    return {
        "message": "JobShield API đang hoạt động",
        "status": "ok",
        "version": "0.1.0",
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
