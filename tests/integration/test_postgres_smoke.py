import os

import pytest
from psycopg.conninfo import conninfo_to_dict

from rental_platform.config import Settings
from rental_platform.generator import build_source_data
from rental_platform.loader import load_staging, read_staging_counts
from rental_platform.validation import validate_and_normalize

pytestmark = pytest.mark.integration


def _integration_settings() -> Settings:
    dsn = os.getenv("RENTAL_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("RENTAL_TEST_POSTGRES_DSN is not configured")
    params = conninfo_to_dict(dsn)
    return Settings(
        _env_file=None,
        postgres_host=params["host"],
        postgres_port=int(params["port"]),
        postgres_user=params["user"],
        postgres_password=params["password"],
        postgres_database=params["dbname"],
        dataset_size=3,
    )


def test_generated_records_reach_postgres_staging() -> None:
    settings = _integration_settings()
    normalized = validate_and_normalize(build_source_data(3, 42))

    loaded = load_staging(normalized, settings)

    assert loaded == read_staging_counts(settings)
    assert loaded["properties"] == 3
    assert loaded["payments"] == 9
