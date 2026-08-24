from pathlib import Path

import pytest
from pydantic import ValidationError

from rental_platform.config import Settings


def test_default_settings_are_safe_for_local_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432
    assert settings.bronze_path == Path("data/bronze")
    assert settings.silver_path == Path("data/silver")
    assert settings.dataset_size == 12
    assert settings.random_seed == 42
    assert "rental_dev" in settings.postgres_dsn


def test_environment_overrides_are_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENTAL_DATASET_SIZE", "7")
    monkeypatch.setenv("RENTAL_POSTGRES_PORT", "5544")
    monkeypatch.setenv("RENTAL_LOG_LEVEL", "debug")

    settings = Settings(_env_file=None)

    assert settings.dataset_size == 7
    assert settings.postgres_port == 5544
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize(
    ("field", "value"),
    [("dataset_size", 0), ("postgres_port", 70_000), ("log_level", "verbose")],
)
def test_invalid_configuration_fails_clearly(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})
