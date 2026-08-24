from pathlib import Path
from urllib.parse import quote

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from RENTAL_* environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RENTAL_",
        case_sensitive=False,
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_user: str = "rental"
    postgres_password: SecretStr = SecretStr("rental_dev")
    postgres_database: str = "rental_analytics"

    bronze_path: Path = Path("data/bronze")
    silver_path: Path = Path("data/silver")
    random_seed: int = 42
    dataset_size: int = Field(default=12, ge=1, le=100_000)
    log_level: str = "INFO"
    spark_master: str = "local[*]"

    @field_validator("postgres_host", "postgres_user", "postgres_database", "spark_master")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return level

    @property
    def postgres_dsn(self) -> str:
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        database = quote(self.postgres_database, safe="")
        return (
            f"postgresql://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{database}"
        )
