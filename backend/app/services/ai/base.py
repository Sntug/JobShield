"""Base interface for AI providers."""

from abc import ABC, abstractmethod
from typing import List

from app.schemas.analyses import AIInsightsData, IndicatorItem, JobExtracted


class BaseAIProvider(ABC):
    """Trừu tượng hóa AI Provider cho phân tích ngữ nghĩa (Layer 2)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên của provider (vd: gemini, openai)."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Tên model đang dùng (vd: gemini-2.5-flash)."""
        pass

    @abstractmethod
    def analyze(
        self,
        text: str,
        job: JobExtracted,
        indicators: List[IndicatorItem],
        risk_label_vi: str,
    ) -> AIInsightsData:
        """Thực hiện phân tích ngữ nghĩa từ văn bản tin tuyển dụng."""
        pass
