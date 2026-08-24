import csv
import json
from pathlib import Path

from rental_platform.errors import PipelineError
from rental_platform.generator import CSV_ENTITIES
from rental_platform.types import Dataset


def read_bronze(bronze_path: Path) -> Dataset:
    """Read generated Bronze CSV and JSON Lines files without Spark."""

    data: Dataset = {}
    for entity in CSV_ENTITIES:
        path = bronze_path / f"{entity}.csv"
        if not path.is_file():
            raise PipelineError(f"Required Bronze file does not exist: {path}")
        with path.open(encoding="utf-8", newline="") as stream:
            data[entity] = [dict(row) for row in csv.DictReader(stream)]

    payments_path = bronze_path / "payments.jsonl"
    if not payments_path.is_file():
        raise PipelineError(f"Required Bronze file does not exist: {payments_path}")
    try:
        with payments_path.open(encoding="utf-8") as stream:
            data["payments"] = [json.loads(line) for line in stream if line.strip()]
    except json.JSONDecodeError as exc:
        raise PipelineError(f"Invalid JSON in Bronze file {payments_path}: {exc}") from exc
    return data
