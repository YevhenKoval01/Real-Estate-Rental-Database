import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb

from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.quality import (
    METADATA_FIELDS,
    QualityResult,
    RejectedRecord,
    json_ready,
    record_fingerprint,
    utc_now,
)
from rental_platform.types import ENTITY_ORDER, Dataset

LOGGER = logging.getLogger(__name__)

BUSINESS_COLUMNS = {
    "locations": ("location_id", "city", "region", "country_code"),
    "owners": ("owner_id", "full_name", "email"),
    "tenants": ("tenant_id", "full_name", "email"),
    "properties": (
        "property_id",
        "location_id",
        "owner_id",
        "property_type",
        "bedrooms",
        "size_sqm",
        "monthly_rent",
        "currency",
    ),
    "rental_agreements": (
        "agreement_id",
        "property_id",
        "tenant_id",
        "start_date",
        "end_date",
        "monthly_rent",
        "status",
    ),
    "payments": (
        "payment_id",
        "agreement_id",
        "due_date",
        "payment_date",
        "amount",
        "status",
    ),
}
METADATA_COLUMNS = ("batch_id", "source_timestamp", "record_fingerprint", "processed_at")
LOAD_COLUMNS = {
    entity: (*columns, *METADATA_COLUMNS) for entity, columns in BUSINESS_COLUMNS.items()
}
PRIMARY_KEYS = {entity: columns[0] for entity, columns in BUSINESS_COLUMNS.items()}


@dataclass(frozen=True)
class LoadMetrics:
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0

    def __add__(self, other: "LoadMetrics") -> "LoadMetrics":
        return LoadMetrics(
            inserted_count=self.inserted_count + other.inserted_count,
            updated_count=self.updated_count + other.updated_count,
            skipped_count=self.skipped_count + other.skipped_count,
        )


def _connect(settings: Settings) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        connect_timeout=10,
    )


def _row_values(row: dict[str, object], columns: Sequence[str]) -> tuple[object, ...]:
    return tuple(row[column] for column in columns)


def start_pipeline_run(settings: Settings, batch_id: str, started_at: datetime) -> None:
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO staging.pipeline_runs (batch_id, started_at, final_status)
                VALUES (%s, %s, 'RUNNING')
                ON CONFLICT (batch_id) DO UPDATE SET
                    started_at = EXCLUDED.started_at,
                    finished_at = NULL,
                    input_count = 0,
                    accepted_count = 0,
                    rejected_count = 0,
                    inserted_count = 0,
                    updated_count = 0,
                    skipped_count = 0,
                    final_status = 'RUNNING',
                    failure_message = NULL
                """,
                (batch_id, started_at),
            )
    except psycopg.Error as exc:
        raise PipelineError(f"Could not start pipeline audit record: {exc}") from exc


def finish_pipeline_run(
    settings: Settings,
    batch_id: str,
    *,
    quality: QualityResult | None,
    metrics: LoadMetrics | None,
    status: str,
    failure_message: str | None = None,
) -> None:
    quality = quality or QualityResult(
        accepted={entity: [] for entity in ENTITY_ORDER}, rejected=(), input_count=0
    )
    metrics = metrics or LoadMetrics()
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE staging.pipeline_runs
                SET finished_at = %s,
                    input_count = %s,
                    accepted_count = %s,
                    rejected_count = %s,
                    inserted_count = %s,
                    updated_count = %s,
                    skipped_count = %s,
                    final_status = %s,
                    failure_message = %s
                WHERE batch_id = %s
                """,
                (
                    utc_now(),
                    quality.input_count,
                    quality.accepted_count,
                    quality.rejected_count,
                    metrics.inserted_count,
                    metrics.updated_count,
                    metrics.skipped_count,
                    status,
                    failure_message[:2000] if failure_message else None,
                    batch_id,
                ),
            )
    except psycopg.Error as exc:
        raise PipelineError(f"Could not finish pipeline audit record: {exc}") from exc


def _load_entity(
    cursor: psycopg.Cursor[tuple[object, ...]], entity: str, rows: list
) -> LoadMetrics:
    columns = LOAD_COLUMNS[entity]
    primary_key = PRIMARY_KEYS[entity]
    cursor.execute(f"SELECT {primary_key}, record_fingerprint FROM staging.{entity}")
    existing = {str(identifier): str(fingerprint) for identifier, fingerprint in cursor.fetchall()}

    inserts = []
    updates = []
    skipped = 0
    for row in rows:
        identifier = str(row[primary_key])
        fingerprint = str(row["record_fingerprint"])
        current = existing.get(identifier)
        if current is None:
            inserts.append(_row_values(row, columns))
        elif current != fingerprint:
            updates.append((*_row_values(row, columns[1:]), identifier))
        else:
            skipped += 1

    if inserts:
        placeholders = ", ".join(["%s"] * len(columns))
        cursor.executemany(
            f"INSERT INTO staging.{entity} ({', '.join(columns)}) VALUES ({placeholders})",
            inserts,
        )
    if updates:
        assignments = ", ".join(f"{column} = %s" for column in columns[1:])
        cursor.executemany(
            f"UPDATE staging.{entity} SET {assignments} WHERE {primary_key} = %s",
            updates,
        )
    return LoadMetrics(len(inserts), len(updates), skipped)


def _load_rejections(
    cursor: psycopg.Cursor[tuple[object, ...]], rejected: Sequence[RejectedRecord]
) -> None:
    if not rejected:
        return
    cursor.executemany(
        """
        INSERT INTO staging.rejected_records (
            record_type, source_identifier, batch_id, reason_code,
            explanation, processed_at, raw_record
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (batch_id, record_type, source_identifier, reason_code)
        DO UPDATE SET
            explanation = EXCLUDED.explanation,
            processed_at = EXCLUDED.processed_at,
            raw_record = EXCLUDED.raw_record
        """,
        [
            (
                record.record_type,
                record.source_identifier,
                record.batch_id,
                record.reason_code,
                record.explanation,
                record.processed_at,
                Jsonb(json_ready(record.raw_record)),
            )
            for record in rejected
        ],
    )


def load_incremental(quality: QualityResult, settings: Settings) -> LoadMetrics:
    """Insert new records, update changed fingerprints, and skip unchanged records."""

    metrics = LoadMetrics()
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('staging.pipeline_runs')")
            if cursor.fetchone()[0] is None:
                raise PipelineError(
                    "Incremental schema is missing; apply warehouse/migrations/"
                    "002_incremental_pipeline.sql"
                )
            _load_rejections(cursor, quality.rejected)
            for entity in ENTITY_ORDER:
                entity_metrics = _load_entity(cursor, entity, quality.accepted[entity])
                metrics += entity_metrics
                LOGGER.info(
                    "Incremental load entity=%s inserted=%d updated=%d skipped=%d",
                    entity,
                    entity_metrics.inserted_count,
                    entity_metrics.updated_count,
                    entity_metrics.skipped_count,
                )
        return metrics
    except PipelineError:
        raise
    except psycopg.Error as exc:
        raise PipelineError(f"PostgreSQL incremental load failed: {exc}") from exc


def _compatibility_quality(data: Dataset, batch_id: str) -> QualityResult:
    processed_at = utc_now()
    accepted: Dataset = {entity: [] for entity in ENTITY_ORDER}
    for entity in ENTITY_ORDER:
        for row in data[entity]:
            business = {key: value for key, value in row.items() if key not in METADATA_FIELDS}
            accepted[entity].append(
                {
                    **row,
                    "batch_id": batch_id,
                    "record_fingerprint": record_fingerprint(business),
                    "processed_at": processed_at,
                }
            )
    return QualityResult(
        accepted=accepted,
        rejected=(),
        input_count=sum(len(rows) for rows in data.values()),
    )


def load_staging(data: Dataset, settings: Settings) -> dict[str, int]:
    """Compatibility helper for the Stage 1 smoke test; Stage 2 uses incremental loading."""

    batch_id = f"compatibility-{utc_now().strftime('%Y%m%dT%H%M%S%f')}"
    quality = _compatibility_quality(data, batch_id)
    start_pipeline_run(settings, batch_id, utc_now())
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE staging.payments, staging.rental_agreements, staging.properties, "
                "staging.tenants, staging.owners, staging.locations"
            )
        metrics = load_incremental(quality, settings)
        finish_pipeline_run(settings, batch_id, quality=quality, metrics=metrics, status="SUCCESS")
        return read_staging_counts(settings)
    except Exception as exc:
        finish_pipeline_run(
            settings,
            batch_id,
            quality=quality,
            metrics=None,
            status="FAILED",
            failure_message=str(exc),
        )
        raise


def read_staging_counts(settings: Settings) -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            for entity in ENTITY_ORDER:
                cursor.execute(f"SELECT count(*) FROM staging.{entity}")
                counts[entity] = int(cursor.fetchone()[0])
        return counts
    except psycopg.Error as exc:
        raise PipelineError(f"Could not read PostgreSQL staging counts: {exc}") from exc


def read_pipeline_run(settings: Settings, batch_id: str) -> dict[str, object]:
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT batch_id, started_at, finished_at, input_count, accepted_count,
                       rejected_count, inserted_count, updated_count, skipped_count,
                       final_status, failure_message
                FROM staging.pipeline_runs
                WHERE batch_id = %s
                """,
                (batch_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise PipelineError(f"Pipeline run does not exist: {batch_id}")
            columns = (
                "batch_id",
                "started_at",
                "finished_at",
                "input_count",
                "accepted_count",
                "rejected_count",
                "inserted_count",
                "updated_count",
                "skipped_count",
                "final_status",
                "failure_message",
            )
            return dict(zip(columns, row, strict=True))
    except PipelineError:
        raise
    except psycopg.Error as exc:
        raise PipelineError(f"Could not read pipeline audit record: {exc}") from exc


def metrics_as_dict(metrics: LoadMetrics) -> dict[str, int]:
    return asdict(metrics)
