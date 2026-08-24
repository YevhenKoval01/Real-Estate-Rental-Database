from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

from rental_platform.errors import DataValidationError
from rental_platform.generator import build_source_data
from rental_platform.validation import validate_and_normalize


def test_validation_normalizes_types_and_text() -> None:
    data = build_source_data(2, 42)
    data["locations"][0]["city"] = "  WARSAW "
    data["owners"][0]["email"] = " OWNER1@EXAMPLE.COM "

    normalized = validate_and_normalize(data)

    assert normalized["locations"][0]["city"] == "Warsaw"
    assert normalized["owners"][0]["email"] == "owner1@example.com"
    assert normalized["properties"][0]["size_sqm"] == Decimal(data["properties"][0]["size_sqm"])
    assert isinstance(normalized["rental_agreements"][0]["start_date"], date)


@pytest.mark.parametrize(
    ("entity", "field", "value", "message"),
    [
        ("properties", "property_id", "", "MISSING_REQUIRED_FIELD"),
        ("properties", "size_sqm", "0", "size_sqm must be positive"),
        ("properties", "monthly_rent", "-1", "monthly_rent must be non-negative"),
        ("rental_agreements", "end_date", "2020-01-01", "end_date must not be before"),
        ("payments", "payment_date", "not-a-date", "must use ISO date format"),
    ],
)
def test_invalid_basic_values_fail_with_explanation(
    entity: str, field: str, value: object, message: str
) -> None:
    data = deepcopy(build_source_data(2, 42))
    data[entity][0][field] = value

    with pytest.raises(DataValidationError, match=message):
        validate_and_normalize(data)


@pytest.mark.parametrize(
    ("entity", "field", "value", "code"),
    [
        ("properties", "owner_id", "OWN-DOES-NOT-EXIST", "ORPHAN_OWNER"),
        ("properties", "location_id", "LOC-DOES-NOT-EXIST", "ORPHAN_LOCATION"),
        ("rental_agreements", "tenant_id", "TEN-DOES-NOT-EXIST", "ORPHAN_TENANT"),
        ("payments", "agreement_id", "AGR-DOES-NOT-EXIST", "ORPHAN_AGREEMENT"),
    ],
)
def test_orphaned_relationships_fail(entity: str, field: str, value: object, code: str) -> None:
    data = deepcopy(build_source_data(2, 42))
    data[entity][0][field] = value

    with pytest.raises(DataValidationError) as captured:
        validate_and_normalize(data)

    assert code in {issue.code for issue in captured.value.issues}


def test_duplicate_identifier_fails() -> None:
    data = deepcopy(build_source_data(2, 42))
    data["payments"].append(deepcopy(data["payments"][0]))

    with pytest.raises(DataValidationError) as captured:
        validate_and_normalize(data)

    assert "DUPLICATE_IDENTIFIER" in {issue.code for issue in captured.value.issues}


def test_payment_due_date_must_fall_within_agreement() -> None:
    data = deepcopy(build_source_data(2, 42))
    data["payments"][0]["due_date"] = "2030-01-01"

    with pytest.raises(DataValidationError) as captured:
        validate_and_normalize(data)

    assert "PAYMENT_DUE_OUTSIDE_AGREEMENT" in {issue.code for issue in captured.value.issues}
