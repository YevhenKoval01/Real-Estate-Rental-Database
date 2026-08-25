import json
import logging
import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import psycopg

from rental_platform.bi_validation import validate_semantic_model
from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.pipeline import PipelineResult, run_pipeline

LOGGER = logging.getLogger(__name__)


def _connect(settings: Settings) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        connect_timeout=10,
    )


def reset_smoke_state(settings: Settings) -> None:
    """Reset only the schemas and tables owned by this development platform."""

    with _connect(settings) as connection, connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS analytics_marts CASCADE")
        cursor.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
        cursor.execute("DROP SCHEMA IF EXISTS analytics_intermediate CASCADE")
        cursor.execute("DROP SCHEMA IF EXISTS analytics_staging CASCADE")
        cursor.execute("DROP SCHEMA IF EXISTS analytics_snapshots CASCADE")
        cursor.execute(
            "TRUNCATE staging.rejected_records, staging.pipeline_runs, staging.payments, "
            "staging.rental_agreements, staging.properties, staging.tenants, "
            "staging.owners, staging.locations RESTART IDENTITY"
        )


def _settings_for(
    settings: Settings,
    *,
    dataset_size: int,
    quality_issues: int = 0,
    rent_adjustment: Decimal = Decimal("0"),
) -> Settings:
    return settings.model_copy(
        update={
            "dataset_size": dataset_size,
            "quality_issue_count": quality_issues,
            "rent_adjustment": rent_adjustment,
        }
    )


def _run_dbt(settings: Settings) -> None:
    executable = shutil.which("dbt")
    if executable is None:
        raise PipelineError("dbt executable is required for the complete smoke test")
    command = [
        executable,
        "build",
        "--project-dir",
        str(settings.dbt_project_path),
        "--profiles-dir",
        str(settings.dbt_project_path),
        "--no-use-colors",
    ]
    completed = subprocess.run(command, env=os.environ.copy(), check=False)
    if completed.returncode:
        raise PipelineError(f"dbt build failed with exit code {completed.returncode}")


def _metrics(result: PipelineResult) -> dict[str, int]:
    return {
        "input": result.quality.input_count,
        "accepted": result.quality.accepted_count,
        "rejected": result.quality.rejected_count,
        "inserted": result.load_metrics.inserted_count,
        "updated": result.load_metrics.updated_count,
        "skipped": result.load_metrics.skipped_count,
    }


def run_complete_smoke_test(settings: Settings, output_path: Path) -> dict[str, object]:
    reset_smoke_state(settings)
    full = run_pipeline(_settings_for(settings, dataset_size=12), batch_id="smoke-full")
    _run_dbt(settings)
    identical = run_pipeline(_settings_for(settings, dataset_size=12), batch_id="smoke-identical")
    expanded = run_pipeline(_settings_for(settings, dataset_size=13), batch_id="smoke-new")
    changed = run_pipeline(
        _settings_for(settings, dataset_size=13, rent_adjustment=Decimal("250")),
        batch_id="smoke-changed",
    )
    _run_dbt(settings)
    invalid = run_pipeline(
        _settings_for(
            settings,
            dataset_size=13,
            quality_issues=9,
            rent_adjustment=Decimal("250"),
        ),
        batch_id="smoke-invalid",
    )
    bi = validate_semantic_model(
        settings.bi_model_path,
        settings.bi_model_path.parent / "semantic-model-contract.json",
    )

    expected = {
        "full": (81, 81, 0, 81, 0, 0),
        "identical": (81, 81, 0, 0, 0, 81),
        "new": (88, 88, 0, 7, 0, 81),
        "changed": (88, 88, 0, 0, 5, 83),
        "invalid": (96, 88, 8, 0, 0, 88),
    }
    runs = {
        "full": _metrics(full),
        "identical": _metrics(identical),
        "new": _metrics(expanded),
        "changed": _metrics(changed),
        "invalid": _metrics(invalid),
    }
    for name, values in expected.items():
        if tuple(runs[name].values()) != values:
            raise PipelineError(
                f"Smoke metrics do not reconcile for {name}: expected {values}, got {runs[name]}"
            )

    with _connect(settings) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*), count(DISTINCT reason_code) FROM staging.rejected_records "
            "WHERE batch_id = 'smoke-invalid'"
        )
        rejected_count, rejection_code_count = cursor.fetchone()
        cursor.execute("SELECT count(*) FROM analytics_snapshots.property_history")
        snapshot_rows = int(cursor.fetchone()[0])
        cursor.execute(
            "SELECT count(*) FROM analytics_snapshots.property_history "
            "WHERE property_id = 'PRP-00001'"
        )
        changed_property_versions = int(cursor.fetchone()[0])

    evidence: dict[str, object] = {
        "runs": runs,
        "rejected_records": int(rejected_count),
        "rejection_reason_codes": int(rejection_code_count),
        "property_snapshot_rows": snapshot_rows,
        "changed_property_versions": changed_property_versions,
        "power_bi": {
            "tables": bi.table_count,
            "measures": bi.measure_count,
            "sources": bi.source_count,
            "desktop_verified": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Complete platform smoke test passed evidence=%s", output_path)
    return evidence
