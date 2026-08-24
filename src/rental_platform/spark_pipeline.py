import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.quality import QualityResult, assess_quality, write_quality_artifacts
from rental_platform.types import ENTITY_ORDER, Dataset

LOGGER = logging.getLogger(__name__)


def _spark_schemas() -> dict[str, Any]:
    from pyspark.sql.types import (
        DateType,
        DecimalType,
        IntegerType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    text = StringType()
    money = DecimalType(12, 2)
    size = DecimalType(10, 2)
    metadata = (
        ("batch_id", text),
        ("record_fingerprint", text),
        ("processed_at", TimestampType()),
    )
    schemas = {
        "locations": (
            ("location_id", text),
            ("city", text),
            ("region", text),
            ("country_code", text),
            ("source_timestamp", TimestampType()),
            *metadata,
        ),
        "owners": (
            ("owner_id", text),
            ("full_name", text),
            ("email", text),
            ("source_timestamp", TimestampType()),
            *metadata,
        ),
        "tenants": (
            ("tenant_id", text),
            ("full_name", text),
            ("email", text),
            ("source_timestamp", TimestampType()),
            *metadata,
        ),
        "properties": (
            ("property_id", text),
            ("location_id", text),
            ("owner_id", text),
            ("property_type", text),
            ("bedrooms", IntegerType()),
            ("size_sqm", size),
            ("monthly_rent", money),
            ("currency", text),
            ("source_timestamp", TimestampType()),
            *metadata,
        ),
        "rental_agreements": (
            ("agreement_id", text),
            ("property_id", text),
            ("tenant_id", text),
            ("start_date", DateType()),
            ("end_date", DateType()),
            ("monthly_rent", money),
            ("status", text),
            ("source_timestamp", TimestampType()),
            *metadata,
        ),
        "payments": (
            ("payment_id", text),
            ("agreement_id", text),
            ("due_date", DateType()),
            ("payment_date", DateType()),
            ("amount", money),
            ("status", text),
            ("source_timestamp", TimestampType()),
            *metadata,
        ),
    }
    return {
        entity: StructType(
            [StructField(name, data_type, nullable=False) for name, data_type in fields]
        )
        for entity, fields in schemas.items()
    }


def _create_spark(settings: Settings) -> Any:
    from pyspark.sql import SparkSession

    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    return (
        SparkSession.builder.appName("rental-platform-stage2")
        .master(settings.spark_master)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def _read_bronze_with_spark(spark: Any, bronze_path: Path) -> Dataset:
    data: Dataset = {}
    for entity in ENTITY_ORDER:
        path = bronze_path / ("payments.jsonl" if entity == "payments" else f"{entity}.csv")
        if not path.is_file():
            raise PipelineError(f"Required Bronze file does not exist: {path}")
        if entity == "payments":
            frame = spark.read.json(str(path))
        else:
            frame = spark.read.option("header", True).option("inferSchema", False).csv(str(path))
        data[entity] = [row.asDict(recursive=True) for row in frame.collect()]
    return data


def transform_bronze_to_silver(
    settings: Settings,
    *,
    batch_id: str,
    processed_at: datetime | None = None,
) -> QualityResult:
    """Read Bronze with Spark, quarantine invalid rows, and write accepted Parquet."""

    spark = None
    try:
        spark = _create_spark(settings)
        spark.sparkContext.setLogLevel("WARN")
        raw = _read_bronze_with_spark(spark, settings.bronze_path)
        quality = assess_quality(raw, batch_id=batch_id, processed_at=processed_at)
        schemas = _spark_schemas()
        for entity in ENTITY_ORDER:
            output_path = settings.silver_path / entity
            frame = spark.createDataFrame(quality.accepted[entity], schema=schemas[entity])
            frame.coalesce(1).write.mode("overwrite").parquet(str(output_path))
            LOGGER.info(
                "Wrote Silver Parquet entity=%s records=%d",
                entity,
                len(quality.accepted[entity]),
            )
        write_quality_artifacts(quality, settings.quality_path, settings.rejected_path)
        LOGGER.info(
            "Quality assessment batch_id=%s input=%d accepted=%d rejected=%d reasons=%s",
            batch_id,
            quality.input_count,
            quality.accepted_count,
            quality.rejected_count,
            quality.reason_counts,
        )
        return quality
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"PySpark transformation failed: {exc}") from exc
    finally:
        if spark is not None:
            spark.stop()


def read_silver(settings: Settings) -> Dataset:
    """Read the current Silver Parquet datasets for an independently scheduled load task."""

    spark = None
    try:
        spark = _create_spark(settings)
        spark.sparkContext.setLogLevel("WARN")
        data: Dataset = {}
        for entity in ENTITY_ORDER:
            path = settings.silver_path / entity
            if not path.is_dir():
                raise PipelineError(f"Required Silver dataset does not exist: {path}")
            data[entity] = [
                row.asDict(recursive=True) for row in spark.read.parquet(str(path)).collect()
            ]
        return data
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"Could not read Silver Parquet: {exc}") from exc
    finally:
        if spark is not None:
            spark.stop()
