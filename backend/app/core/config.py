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
