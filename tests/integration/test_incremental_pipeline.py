import os
from datetime import UTC, datetime
from decimal import Decimal

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

from rental_platform.config import Settings
from rental_platform.generator import build_source_data
from rental_platform.loader import (
    finish_pipeline_run,
    load_incremental,
    read_pipeline_run,
    start_pipeline_run,
)
from rental_platform.quality import assess_quality

pytestmark = pytest.mark.integration


def _settings() -> tuple[Settings, str]:
    dsn = os.getenv("RENTAL_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("RENTAL_TEST_POSTGRES_DSN is not configured")
    params = conninfo_to_dict(dsn)
    return (
        Settings(
            _env_file=None,
            postgres_host=params["host"],
            postgres_port=int(params["port"]),
            postgres_user=params["user"],
            postgres_password=params["password"],
            postgres_database=params["dbname"],
        ),
        dsn,
    )


def _reset_stage2_tables(dsn: str) -> None:
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE staging.rejected_records, staging.pipeline_runs, staging.payments, "
            "staging.rental_agreements, staging.properties, staging.tenants, "
            "staging.owners, staging.locations RESTART IDENTITY"
        )


def _load(settings: Settings, data, batch_id: str):
    quality = assess_quality(
        data,
        batch_id=batch_id,
        processed_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    start_pipeline_run(settings, batch_id, datetime(2025, 1, 1, tzinfo=UTC))
    metrics = load_incremental(quality, settings)
    finish_pipeline_run(settings, batch_id, quality=quality, metrics=metrics, status="SUCCESS")
    return quality, metrics


def test_full_idempotent_changed_and_invalid_batches() -> None:
    settings, dsn = _settings()
    _reset_stage2_tables(dsn)

    first_quality, first = _load(settings, build_source_data(12, 42), "full-load")
    _, second = _load(settings, build_source_data(12, 42), "identical-load")
    _, expanded = _load(settings, build_source_data(13, 42), "new-records-load")
    changed_source = build_source_data(13, 42, rent_adjustment=Decimal("250"))
    _, changed = _load(
        settings,
        changed_source,
        "changed-load",
    )
    invalid_quality, invalid = _load(
        settings,
        build_source_data(
            13,
            42,
            quality_issue_count=9,
            rent_adjustment=Decimal("250"),
        ),
        "invalid-load",
    )

    assert first_quality.accepted_count == 81
    assert (first.inserted_count, first.updated_count, first.skipped_count) == (81, 0, 0)
    assert (second.inserted_count, second.updated_count, second.skipped_count) == (0, 0, 81)
    assert (expanded.inserted_count, expanded.updated_count, expanded.skipped_count) == (7, 0, 81)
    assert (changed.inserted_count, changed.updated_count, changed.skipped_count) == (0, 5, 83)
    assert invalid_quality.rejected_count == 8
    assert (invalid.inserted_count, invalid.updated_count, invalid.skipped_count) == (0, 0, 88)

    audit = read_pipeline_run(settings, "invalid-load")
    assert audit["input_count"] == 96
    assert audit["accepted_count"] == 88
    assert audit["rejected_count"] == 8
    assert audit["skipped_count"] == 88
    assert audit["final_status"] == "SUCCESS"

    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT monthly_rent FROM staging.properties WHERE property_id = 'PRP-00001'"
        )
        assert cursor.fetchone()[0] == Decimal(changed_source["properties"][0]["monthly_rent"])
        cursor.execute(
            "SELECT count(*), count(DISTINCT reason_code) "
            "FROM staging.rejected_records WHERE batch_id = 'invalid-load'"
        )
        assert cursor.fetchone() == (8, 7)


def test_failed_run_can_be_audited() -> None:
    settings, _ = _settings()
    start_pipeline_run(settings, "failed-load", datetime(2025, 1, 1, tzinfo=UTC))
    finish_pipeline_run(
        settings,
        "failed-load",
        quality=None,
        metrics=None,
        status="FAILED",
        failure_message="simulated source failure",
    )

    audit = read_pipeline_run(settings, "failed-load")
    assert audit["final_status"] == "FAILED"
    assert audit["failure_message"] == "simulated source failure"
