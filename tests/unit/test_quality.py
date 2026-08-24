from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from rental_platform.generator import build_source_data
from rental_platform.quality import (
    assess_quality,
    read_rejected_records,
    write_quality_artifacts,
)


def test_standard_quality_profile_is_deterministic_and_reconciles() -> None:
    source = build_source_data(12, 42, quality_issue_count=9)

    result = assess_quality(
        source,
        batch_id="quality-test",
        processed_at=datetime(2025, 1, 1, tzinfo=UTC),
    )

    assert result.input_count == 89
    assert result.accepted_count == 81
    assert result.rejected_count == 8
    assert result.input_count == result.accepted_count + result.rejected_count
    assert result.reason_counts == {
        "DUPLICATE_IDENTIFIER": 2,
        "MISSING_REQUIRED_FIELD": 1,
        "INVALID_DATE": 1,
        "INVALID_AGREEMENT_RANGE": 1,
        "INVALID_PROPERTY_SIZE": 1,
        "INVALID_RENT": 1,
        "ORPHAN_OWNER": 1,
    }
    assert result.accepted["locations"][0]["city"] == "Warsaw"


def test_fingerprint_excludes_run_metadata_but_detects_business_change() -> None:
    source = build_source_data(2, 42)
    first = assess_quality(
        source,
        batch_id="first",
        processed_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    second = assess_quality(
        source,
        batch_id="second",
        processed_at=datetime(2025, 1, 2, tzinfo=UTC),
    )
    changed = assess_quality(
        build_source_data(2, 42, rent_adjustment=Decimal("250")),
        batch_id="changed",
        processed_at=datetime(2025, 1, 3, tzinfo=UTC),
    )

    assert (
        first.accepted["properties"][0]["record_fingerprint"]
        == second.accepted["properties"][0]["record_fingerprint"]
    )
    assert (
        first.accepted["properties"][0]["record_fingerprint"]
        != changed.accepted["properties"][0]["record_fingerprint"]
    )
    assert (
        first.accepted["properties"][1]["record_fingerprint"]
        == changed.accepted["properties"][1]["record_fingerprint"]
    )


def test_rejected_artifacts_round_trip(tmp_path: Path) -> None:
    processed_at = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(seconds=1)
    result = assess_quality(
        build_source_data(3, 42, quality_issue_count=3),
        batch_id="artifact-test",
        processed_at=processed_at,
    )

    write_quality_artifacts(result, tmp_path / "quality", tmp_path / "rejected")
    reloaded = read_rejected_records(tmp_path / "rejected", "artifact-test")

    assert len(reloaded) == 3
    assert {record.reason_code for record in reloaded} == {
        "DUPLICATE_IDENTIFIER",
        "MISSING_REQUIRED_FIELD",
        "INVALID_DATE",
    }
    assert (tmp_path / "quality" / "artifact-test" / "summary.json").is_file()
