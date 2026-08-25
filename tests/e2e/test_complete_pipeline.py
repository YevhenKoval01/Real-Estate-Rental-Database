import os
import shutil
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

from rental_platform.config import Settings
from rental_platform.pipeline import run_pipeline

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


def test_source_to_silver_to_postgres_is_recoverable_and_idempotent(tmp_path: Path) -> None:
    if shutil.which("java") is None and not os.getenv("JAVA_HOME"):
        pytest.skip("Java 17 is required for the PySpark end-to-end test")
    dsn = os.getenv("RENTAL_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("RENTAL_TEST_POSTGRES_DSN is not configured")
    params = conninfo_to_dict(dsn)
    settings = Settings(
        _env_file=None,
        postgres_host=params["host"],
        postgres_port=int(params["port"]),
        postgres_user=params["user"],
        postgres_password=params["password"],
        postgres_database=params["dbname"],
        dataset_size=3,
        source_path=tmp_path / "source",
        bronze_path=tmp_path / "bronze",
        quality_path=tmp_path / "quality",
        rejected_path=tmp_path / "rejected",
        silver_path=tmp_path / "silver",
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE staging.rejected_records, staging.pipeline_runs, staging.payments, "
            "staging.rental_agreements, staging.properties, staging.tenants, "
            "staging.owners, staging.locations RESTART IDENTITY"
        )

    first = run_pipeline(settings, batch_id="e2e-full")
    repeated = run_pipeline(settings, batch_id="e2e-repeated")

    assert first.load_metrics.inserted_count == first.quality.accepted_count
    assert repeated.load_metrics.inserted_count == 0
    assert repeated.load_metrics.updated_count == 0
    assert repeated.load_metrics.skipped_count == first.quality.accepted_count
    assert (settings.bronze_path / "properties.csv").is_file()
    assert next((settings.silver_path / "properties").glob("*.parquet")).is_file()
