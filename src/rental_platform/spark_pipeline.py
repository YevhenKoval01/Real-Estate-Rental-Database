import logging
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.types import ENTITY_ORDER, Dataset
from rental_platform.validation import validate_and_normalize

LOGGER = logging.getLogger(__name__)


def _spark_schemas() -> dict[str, Any]:
    from pyspark.sql.types import (
        DateType,
        DecimalType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )

    text = StringType()
    money = DecimalType(12, 2)
    size = DecimalType(10, 2)
    schemas = {
        "locations": (
            ("location_id", text),
            ("city", text),
            ("region", text),
            ("country_code", text),
        ),
        "owners": (("owner_id", text), ("full_name", text), ("email", text)),
        "tenants": (("tenant_id", text), ("full_name", text), ("email", text)),
        "properties": (
            ("property_id", text),
            ("location_id", text),
            ("owner_id", text),
            ("property_type", text),
            ("bedrooms", IntegerType()),
            ("size_sqm", size),
            ("monthly_rent", money),
            ("currency", text),
        ),
        "rental_agreements": (
            ("agreement_id", text),
            ("property_id", text),
            ("tenant_id", text),
            ("start_date", DateType()),
            ("end_date", DateType()),
            ("monthly_rent", money),
            ("status", text),
        ),
        "payments": (
            ("payment_id", text),
            ("agreement_id", text),
            ("due_date", DateType()),
            ("payment_date", DateType()),
            ("amount", money),
            ("status", text),
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
        SparkSession.builder.appName("rental-platform-stage1")
        .master(settings.spark_master)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def _read_bronze_with_spark(spark: Any, bronze_path: Path) -> Dataset:
    data: Dataset = {}
    for entity in ENTITY_ORDER:
        if entity == "payments":
            path = bronze_path / "payments.jsonl"
        else:
            path = bronze_path / f"{entity}.csv"
        if not path.is_file():
            raise PipelineError(f"Required Bronze file does not exist: {path}")
        if entity == "payments":
            reader = spark.read.json(str(path))
        else:
            reader = spark.read.option("header", True).option("inferSchema", False).csv(str(path))
        data[entity] = [row.asDict(recursive=True) for row in reader.collect()]
    return data


def transform_bronze_to_silver(settings: Settings) -> Dataset:
    """Use PySpark to read Bronze files and write validated Silver Parquet datasets."""

    spark = None
    try:
        spark = _create_spark(settings)
        spark.sparkContext.setLogLevel("WARN")
        raw = _read_bronze_with_spark(spark, settings.bronze_path)
        normalized = validate_and_normalize(raw)
        schemas = _spark_schemas()
        for entity in ENTITY_ORDER:
            output_path = settings.silver_path / entity
            frame = spark.createDataFrame(normalized[entity], schema=schemas[entity])
            frame.coalesce(1).write.mode("overwrite").parquet(str(output_path))
            LOGGER.info(
                "Wrote Silver Parquet entity=%s records=%d", entity, len(normalized[entity])
            )
        return normalized
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"PySpark transformation failed: {exc}") from exc
    finally:
        if spark is not None:
            spark.stop()


def decimal_is_supported(value: object) -> bool:
    """Expose the Silver numeric contract for a lightweight unit check."""

    return isinstance(value, Decimal)
