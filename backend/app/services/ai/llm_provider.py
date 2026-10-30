"""LLM Provider implementations using httpx for Gemini and OpenAI-compatible APIs."""

import json
import re
from typing import List, Optional
import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.schemas.analyses import AIInsightsData, IndicatorItem, JobExtracted
from app.services.ai.base import BaseAIProvider
from app.services.ai.prompts import SYSTEM_PROMPT, build_user_prompt


class _LLMOutput(BaseModel):
    """Validate provider output without tightening the saved/fallback schema."""

    model_config = ConfigDict(
        strict=True,
        str_strip_whitespace=True,
        str_min_length=1,
        hide_input_in_errors=True,
    )

    semantic_summary_vi: str
    suspicious_patterns_vi: List[str] = Field(max_length=5)
    reasoning_vi: str
    confidence_note_vi: str


def _parse_llm_json(raw_text: str) -> _LLMOutput:
    """Trích xuất và parse JSON an toàn từ phản hồi của LLM."""
    clean = raw_text.strip()
    # Loại bỏ code block markdown nếu model sinh ra
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if match:
        clean = match.group(1).strip()
    elif clean.startswith("```") and clean.endswith("```"):
        clean = clean[3:-3].strip()
        if clean.startswith("json"):
            clean = clean[4:].strip()

    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError("Phản hồi LLM không phải là JSON object")
    return _LLMOutput.model_validate(parsed)


class GeminiProvider(BaseAIProvider):
    """Provider kết nối trực tiếp Google Gemini API qua REST API bằng httpx."""

    def __init__(
        self,
        api_key: SecretStr,
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 10.0,
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._base_url = (
            base_url.rstrip("/")
            if base_url
            else "https://generativelanguage.googleapis.com/v1beta"
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    def analyze(
        self,
        text: str,
        job: JobExtracted,
        indicators: List[IndicatorItem],
        risk_label_vi: str,
    ) -> AIInsightsData:
        key = self._api_key.get_secret_value()
        url = f"{self._base_url}/models/{self._model}:generateContent?key={key}"

        user_prompt = build_user_prompt(
            text=text,
            company_name=job.company_name,
            job_title=job.job_title,
            detected_rule_categories=[ind.category_vi for ind in indicators],
            current_risk_label=risk_label_vi,
        )

        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini API không trả về candidate nào.")

        first_cand = candidates[0]
        content_parts = first_cand.get("content", {}).get("parts", [])
        if not content_parts or "text" not in content_parts[0]:
            raise ValueError("Gemini API candidate không có text hợp lệ.")

        raw_text = content_parts[0]["text"]
        parsed = _parse_llm_json(raw_text)

        return AIInsightsData(
            status="success",
            provider=self.name,
            model=self.model,
            semantic_summary_vi=parsed.semantic_summary_vi,
            suspicious_patterns_vi=parsed.suspicious_patterns_vi,
            reasoning_vi=parsed.reasoning_vi,
            confidence_note_vi=parsed.confidence_note_vi,
            limitations_vi=[
                f"Phân tích ngữ nghĩa do mô hình {self.name}/{self.model} tạo ra dựa trên văn bản được cung cấp; không thay thế thẩm tra pháp lý hoặc kiểm chứng thực tế."
            ],
        )


class OpenAICompatibleProvider(BaseAIProvider):
    """Provider kết nối tới bất kỳ endpoint tương thích OpenAI qua REST API bằng httpx."""

    def __init__(
        self,
        api_key: SecretStr,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 10.0,
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._base_url = (
            base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def analyze(
        self,
        text: str,
        job: JobExtracted,
        indicators: List[IndicatorItem],
        risk_label_vi: str,
    ) -> AIInsightsData:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        user_prompt = build_user_prompt(
            text=text,
            company_name=job.company_name,
            job_title=job.job_title,
            detected_rule_categories=[ind.category_vi for ind in indicators],
            current_risk_label=risk_label_vi,
        )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("OpenAI API không trả về choice nào.")

        message = choices[0].get("message", {})
        raw_text = message.get("content", "")
        parsed = _parse_llm_json(raw_text)

        return AIInsightsData(
            status="success",
            provider=self.name,
            model=self.model,
            semantic_summary_vi=parsed.semantic_summary_vi,
            suspicious_patterns_vi=parsed.suspicious_patterns_vi,
            reasoning_vi=parsed.reasoning_vi,
            confidence_note_vi=parsed.confidence_note_vi,
            limitations_vi=[
                f"Phân tích ngữ nghĩa do mô hình {self.name}/{self.model} tạo ra dựa trên văn bản được cung cấp; không thay thế thẩm tra pháp lý hoặc kiểm chứng thực tế."
            ],
        )


def get_ai_provider(
    provider_name: str,
    api_key: Optional[SecretStr],
    model: str = "gemini-2.5-flash",
    timeout_seconds: float = 10.0,
    base_url: Optional[str] = None,
) -> Optional[BaseAIProvider]:
    """Factory khởi tạo AI provider tương ứng."""
    clean_provider = provider_name.strip().lower() if provider_name else "none"
    if clean_provider == "none" or not api_key:
        return None

    if clean_provider == "gemini":
        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )

    if clean_provider in ("openai", "openai-compatible"):
        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )

    return None
