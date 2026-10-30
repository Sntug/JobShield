from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        hide_input_in_errors=True,
    )

    database_url: SecretStr = Field(validation_alias="DATABASE_URL", min_length=1)

    # Cấu hình AI Provider (R5)
    ai_provider: str = Field(default="none", validation_alias="AI_PROVIDER")
    ai_api_key: Optional[SecretStr] = Field(default=None, validation_alias="AI_API_KEY")
    ai_model: str = Field(default="gemini-2.5-flash", validation_alias="AI_MODEL")
    ai_timeout_seconds: float = Field(default=10.0, validation_alias="AI_TIMEOUT_SECONDS")
    ai_base_url: Optional[str] = Field(default=None, validation_alias="AI_BASE_URL")
