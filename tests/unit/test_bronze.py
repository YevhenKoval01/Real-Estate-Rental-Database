from pathlib import Path

import pytest

from rental_platform.bronze import read_bronze
from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.generator import generate_source_data


def test_bronze_reader_loads_csv_and_json(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, bronze_path=tmp_path, dataset_size=3)
    expected = generate_source_data(settings)

    actual = read_bronze(tmp_path)

    assert actual["locations"] == expected["locations"]
    assert actual["payments"] == expected["payments"]


def test_bronze_reader_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PipelineError, match="Required Bronze file does not exist"):
        read_bronze(tmp_path)


def test_bronze_reader_reports_invalid_json(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, bronze_path=tmp_path, dataset_size=1)
    generate_source_data(settings)
    (tmp_path / "payments.jsonl").write_text("{invalid}\n", encoding="utf-8")

    with pytest.raises(PipelineError, match="Invalid JSON"):
        read_bronze(tmp_path)
