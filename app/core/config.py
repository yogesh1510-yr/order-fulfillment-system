from functools import lru_cache

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    # Application

    app_name: str = "E-Commerce Order and Fulfillment Platform"

    app_version: str = "1.0.0"

    environment: str = "development"

    debug: bool = False

    # Database

    database_url: str = Field(validation_alias="DATABASE_URL")

    db_echo: bool = False

    db_pool_size: int = Field(
        default=5,
        ge=1,
    )

    db_max_overflow: int = Field(
        default=10,
        ge=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
