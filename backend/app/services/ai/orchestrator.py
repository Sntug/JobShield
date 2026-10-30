"""Orchestrator for AI-assisted semantic analysis and robust fallbacks."""

import logging
from typing import List, Optional
import httpx

from app.core.config import Settings
from app.schemas.analyses import AIInsightsData, IndicatorItem, JobExtracted
from app.services.ai.llm_provider import get_ai_provider

logger = logging.getLogger("uvicorn.error")


def run_ai_assisted_analysis(
    text: str,
    job: JobExtracted,
    indicators: List[IndicatorItem],
    risk_label_vi: str,
    use_ai: bool = False,
    ai_consent: bool = False,
    settings: Optional[Settings] = None,
) -> Optional[AIInsightsData]:
    """Thực hiện phân tích ngữ nghĩa AI (Layer 2) với cơ chế fallback toàn diện.

    Ranh giới an toàn:
    - Nếu không yêu cầu AI (use_ai=False): trả về None (thuần rule-based).
    - Nếu không consent (ai_consent=False): từ chối gọi provider, trả fallback_no_consent.
    - Nếu chưa bật provider hoặc thiếu API key: trả fallback_disabled / fallback_missing_key.
    - Nếu mạng lỗi, timeout, rate limit hoặc output hỏng: bắt lỗi và trả fallback an toàn.
    """
    if not use_ai:
        return None

    if not ai_consent:
        return AIInsightsData(
            status="fallback_no_consent",
            limitations_vi=[
                "Người dùng chưa đồng ý gửi nội dung tin tuyển dụng tới dịch vụ AI bên ngoài; hệ thống đã giữ nguyên kết quả phân tích theo tập quy tắc chuẩn."
            ],
        )

    if settings is None:
        try:
            settings = Settings()
        except Exception as exc:
            logger.warning("Không thể tải cấu hình Settings cho AI: %s", type(exc).__name__)
            return AIInsightsData(
                status="fallback_error",
                limitations_vi=[
                    "Không thể tải cấu hình hệ thống cho dịch vụ AI; đã tự động quay về phân tích theo quy tắc chuẩn."
                ],
            )

    provider_name = (settings.ai_provider or "none").strip().lower()
    if provider_name == "none":
        return AIInsightsData(
            status="fallback_disabled",
            provider="none",
            limitations_vi=[
                "Tính năng phân tích ngữ nghĩa AI hiện chưa được kích hoạt trên hệ thống; đã tự động chuyển về phân tích theo quy tắc chuẩn."
            ],
        )

    if not settings.ai_api_key or not settings.ai_api_key.get_secret_value().strip():
        return AIInsightsData(
            status="fallback_missing_key",
            provider=provider_name,
            model=settings.ai_model,
            limitations_vi=[
                "Hệ thống chưa cấu hình API key cho dịch vụ AI; đã tự động quay về phân tích theo quy tắc chuẩn."
            ],
        )

    provider = get_ai_provider(
        provider_name=provider_name,
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
        base_url=settings.ai_base_url,
    )

    if provider is None:
        return AIInsightsData(
            status="fallback_disabled",
            provider=provider_name,
            limitations_vi=[
                f"Nhà cung cấp AI '{provider_name}' không được hỗ trợ; đã tự động chuyển về phân tích theo quy tắc chuẩn."
            ],
        )

    try:
        insights = provider.analyze(
            text=text,
            job=job,
            indicators=indicators,
            risk_label_vi=risk_label_vi,
        )
        return insights
    except httpx.TimeoutException:
        logger.warning("Dịch vụ AI timeout sau %s giây", settings.ai_timeout_seconds)
        return AIInsightsData(
            status="fallback_timeout",
            provider=provider.name,
            model=provider.model,
            limitations_vi=[
                "Dịch vụ AI phản hồi quá thời gian quy định (timeout); hệ thống đã tự động quay về phân tích theo tập quy tắc chuẩn an toàn."
            ],
        )
    except httpx.HTTPStatusError as exc:
        logger.warning("Dịch vụ AI trả về mã lỗi HTTP: %s", exc.response.status_code)
        return AIInsightsData(
            status="fallback_error",
            provider=provider.name,
            model=provider.model,
            limitations_vi=[
                f"Dịch vụ AI phản hồi lỗi HTTP ({exc.response.status_code}); hệ thống đã tự động quay về phân tích theo tập quy tắc chuẩn an toàn."
            ],
        )
    except Exception as exc:
        logger.warning("Lỗi phân tích ngữ nghĩa AI: %s", type(exc).__name__)
        return AIInsightsData(
            status="fallback_error",
            provider=provider.name,
            model=provider.model,
            limitations_vi=[
                f"Gặp sự cố khi xử lý phân tích ngữ nghĩa AI ({type(exc).__name__}); hệ thống đã tự động quay về phân tích theo tập quy tắc chuẩn an toàn."
            ],
        )
