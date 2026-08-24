import logging
from dataclasses import dataclass

from rental_platform.config import Settings
from rental_platform.generator import generate_source_data
from rental_platform.loader import load_staging
from rental_platform.spark_pipeline import transform_bronze_to_silver

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    bronze_counts: dict[str, int]
    silver_counts: dict[str, int]
    staging_counts: dict[str, int]


def run_pipeline(settings: Settings, *, skip_load: bool = False) -> PipelineResult:
    """Run the deterministic Stage 1 vertical slice."""

    LOGGER.info(
        "Starting Stage 1 pipeline dataset_size=%d seed=%d",
        settings.dataset_size,
        settings.random_seed,
    )
    bronze = generate_source_data(settings)
    silver = transform_bronze_to_silver(settings)
    staging_counts = {} if skip_load else load_staging(silver, settings)
    result = PipelineResult(
        bronze_counts={entity: len(rows) for entity, rows in bronze.items()},
        silver_counts={entity: len(rows) for entity, rows in silver.items()},
        staging_counts=staging_counts,
    )
    LOGGER.info("Stage 1 pipeline completed result=%s", result)
    return result
