import logging
from dataclasses import dataclass
from time import perf_counter

from rental_platform.bronze import read_bronze
from rental_platform.config import Settings
from rental_platform.generator import generate_source_files, ingest_source_files
from rental_platform.loader import (
    LoadMetrics,
    finish_pipeline_run,
    load_incremental,
    read_pipeline_run,
    start_pipeline_run,
)
from rental_platform.quality import (
    QualityResult,
    assess_quality,
    create_batch_id,
    read_rejected_records,
    utc_now,
    write_quality_artifacts,
)
from rental_platform.spark_pipeline import (
    read_silver,
    transform_bronze_to_silver,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    batch_id: str
    bronze_counts: dict[str, int]
    silver_counts: dict[str, int]
    quality: QualityResult
    load_metrics: LoadMetrics


def validate_bronze_batch(settings: Settings, batch_id: str) -> QualityResult:
    quality = assess_quality(read_bronze(settings.bronze_path), batch_id=batch_id)
    write_quality_artifacts(quality, settings.quality_path, settings.rejected_path)
    LOGGER.info(
        "Validation completed batch_id=%s input=%d accepted=%d rejected=%d",
        batch_id,
        quality.input_count,
        quality.accepted_count,
        quality.rejected_count,
    )
    return quality


def load_silver_batch(settings: Settings, batch_id: str) -> LoadMetrics:
    accepted = read_silver(settings)
    rejected = read_rejected_records(settings.rejected_path, batch_id)
    quality = QualityResult(
        accepted=accepted,
        rejected=rejected,
        input_count=sum(len(rows) for rows in accepted.values()) + len(rejected),
    )
    start_pipeline_run(settings, batch_id, utc_now())
    try:
        metrics = load_incremental(quality, settings)
        finish_pipeline_run(settings, batch_id, quality=quality, metrics=metrics, status="SUCCESS")
        return metrics
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


def publish_run_summary(settings: Settings, batch_id: str) -> dict[str, object]:
    summary = read_pipeline_run(settings, batch_id)
    LOGGER.info("Pipeline run summary=%s", summary)
    return summary


def run_pipeline(
    settings: Settings,
    *,
    batch_id: str | None = None,
    skip_load: bool = False,
) -> PipelineResult:
    """Run source generation through incremental PostgreSQL loading."""

    current_batch = batch_id or create_batch_id()
    started_clock = perf_counter()
    started_at = utc_now()
    audit_started = False
    quality: QualityResult | None = None
    metrics = LoadMetrics()
    LOGGER.info(
        "Starting rental analytics pipeline batch_id=%s dataset_size=%d seed=%d quality_issues=%d",
        current_batch,
        settings.dataset_size,
        settings.random_seed,
        settings.quality_issue_count,
        extra={"event": "pipeline_started", "batch_id": current_batch, "stage": "pipeline"},
    )
    if not skip_load:
        start_pipeline_run(settings, current_batch, started_at)
        audit_started = True

    try:
        source = generate_source_files(settings)
        ingest_source_files(settings)
        quality = transform_bronze_to_silver(
            settings,
            batch_id=current_batch,
            processed_at=started_at,
        )
        if not skip_load:
            metrics = load_incremental(quality, settings)
            finish_pipeline_run(
                settings,
                current_batch,
                quality=quality,
                metrics=metrics,
                status="SUCCESS",
            )
        result = PipelineResult(
            batch_id=current_batch,
            bronze_counts={entity: len(rows) for entity, rows in source.items()},
            silver_counts={entity: len(rows) for entity, rows in quality.accepted.items()},
            quality=quality,
            load_metrics=metrics,
        )
        LOGGER.info(
            "Rental analytics pipeline completed batch_id=%s input=%d accepted=%d rejected=%d "
            "inserted=%d updated=%d skipped=%d",
            result.batch_id,
            result.quality.input_count,
            result.quality.accepted_count,
            result.quality.rejected_count,
            result.load_metrics.inserted_count,
            result.load_metrics.updated_count,
            result.load_metrics.skipped_count,
            extra={
                "event": "pipeline_completed",
                "batch_id": current_batch,
                "stage": "pipeline",
                "input_count": result.quality.input_count,
                "accepted_count": result.quality.accepted_count,
                "rejected_count": result.quality.rejected_count,
                "inserted_count": result.load_metrics.inserted_count,
                "updated_count": result.load_metrics.updated_count,
                "skipped_count": result.load_metrics.skipped_count,
                "duration_ms": round((perf_counter() - started_clock) * 1000, 2),
            },
        )
        return result
    except Exception as exc:
        LOGGER.exception(
            "Rental analytics pipeline failed batch_id=%s",
            current_batch,
            extra={
                "event": "pipeline_failed",
                "batch_id": current_batch,
                "stage": "pipeline",
                "duration_ms": round((perf_counter() - started_clock) * 1000, 2),
            },
        )
        if audit_started:
            finish_pipeline_run(
                settings,
                current_batch,
                quality=quality,
                metrics=metrics,
                status="FAILED",
                failure_message=str(exc),
            )
        raise
