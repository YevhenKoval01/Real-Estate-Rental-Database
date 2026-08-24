from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from rental_platform.errors import DataValidationError, ValidationIssue
from rental_platform.types import ENTITY_ORDER, Dataset, Record

REQUIRED_FIELDS = {
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

IDENTIFIER_FIELDS = {
    "locations": "location_id",
    "owners": "owner_id",
    "tenants": "tenant_id",
    "properties": "property_id",
    "rental_agreements": "agreement_id",
    "payments": "payment_id",
}


def _text(value: object) -> str:
    return str(value).strip()


def _integer(value: object, field: str) -> int:
    try:
        return int(_text(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc


def _decimal(value: object, field: str) -> Decimal:
    try:
        result = Decimal(_text(value)).quantize(Decimal("0.01"))
        if not result.is_finite():
            raise ValueError
        return result
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite decimal number") from exc


def _date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(_text(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must use ISO date format YYYY-MM-DD") from exc


def _normalize_location(row: Record) -> Record:
    country_code = _text(row["country_code"]).upper()
    if len(country_code) != 2:
        raise ValueError("country_code must contain two letters")
    return {
        "location_id": _text(row["location_id"]),
        "city": _text(row["city"]).title(),
        "region": _text(row["region"]).title(),
        "country_code": country_code,
    }


def _normalize_person(row: Record, identifier: str) -> Record:
    return {
        identifier: _text(row[identifier]),
        "full_name": " ".join(_text(row["full_name"]).split()),
        "email": _text(row["email"]).lower(),
    }


def _normalize_property(row: Record) -> Record:
    size_sqm = _decimal(row["size_sqm"], "size_sqm")
    monthly_rent = _decimal(row["monthly_rent"], "monthly_rent")
    bedrooms = _integer(row["bedrooms"], "bedrooms")
    if size_sqm <= 0:
        raise ValueError("size_sqm must be positive")
    if monthly_rent < 0:
        raise ValueError("monthly_rent must be non-negative")
    if bedrooms < 0:
        raise ValueError("bedrooms must be non-negative")
    return {
        "property_id": _text(row["property_id"]),
        "location_id": _text(row["location_id"]),
        "owner_id": _text(row["owner_id"]),
        "property_type": _text(row["property_type"]).lower(),
        "bedrooms": bedrooms,
        "size_sqm": size_sqm,
        "monthly_rent": monthly_rent,
        "currency": _text(row["currency"]).upper(),
    }


def _normalize_agreement(row: Record) -> Record:
    start_date = _date(row["start_date"], "start_date")
    end_date = _date(row["end_date"], "end_date")
    monthly_rent = _decimal(row["monthly_rent"], "monthly_rent")
    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")
    if monthly_rent < 0:
        raise ValueError("monthly_rent must be non-negative")
    return {
        "agreement_id": _text(row["agreement_id"]),
        "property_id": _text(row["property_id"]),
        "tenant_id": _text(row["tenant_id"]),
        "start_date": start_date,
        "end_date": end_date,
        "monthly_rent": monthly_rent,
        "status": _text(row["status"]).upper(),
    }


def _normalize_payment(row: Record) -> Record:
    amount = _decimal(row["amount"], "amount")
    if amount < 0:
        raise ValueError("amount must be non-negative")
    return {
        "payment_id": _text(row["payment_id"]),
        "agreement_id": _text(row["agreement_id"]),
        "due_date": _date(row["due_date"], "due_date"),
        "payment_date": _date(row["payment_date"], "payment_date"),
        "amount": amount,
        "status": _text(row["status"]).upper(),
    }


NORMALIZERS: dict[str, Callable[[Record], Record]] = {
    "locations": _normalize_location,
    "owners": lambda row: _normalize_person(row, "owner_id"),
    "tenants": lambda row: _normalize_person(row, "tenant_id"),
    "properties": _normalize_property,
    "rental_agreements": _normalize_agreement,
    "payments": _normalize_payment,
}


def _value_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _normalize_entities(data: Dataset) -> tuple[Dataset, list[ValidationIssue]]:
    normalized: Dataset = {entity: [] for entity in ENTITY_ORDER}
    issues: list[ValidationIssue] = []

    for entity in ENTITY_ORDER:
        if entity not in data:
            issues.append(ValidationIssue(entity, 0, "MISSING_ENTITY", "source entity is absent"))
            continue

        seen_identifiers: set[str] = set()
        identifier_field = IDENTIFIER_FIELDS[entity]
        for row_number, row in enumerate(data[entity], start=1):
            missing = [field for field in REQUIRED_FIELDS[entity] if _value_missing(row.get(field))]
            if missing:
                issues.append(
                    ValidationIssue(
                        entity,
                        row_number,
                        "MISSING_REQUIRED_FIELD",
                        f"required value(s) missing: {', '.join(missing)}",
                    )
                )
                continue
            try:
                result = NORMALIZERS[entity](row)
            except ValueError as exc:
                issues.append(ValidationIssue(entity, row_number, "INVALID_VALUE", str(exc)))
                continue

            identifier = str(result[identifier_field])
            if identifier in seen_identifiers:
                issues.append(
                    ValidationIssue(
                        entity,
                        row_number,
                        "DUPLICATE_IDENTIFIER",
                        f"{identifier_field} '{identifier}' occurs more than once",
                    )
                )
                continue
            seen_identifiers.add(identifier)
            normalized[entity].append(result)
    return normalized, issues


def _relationship_issues(data: Dataset) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    location_ids = {row["location_id"] for row in data["locations"]}
    owner_ids = {row["owner_id"] for row in data["owners"]}
    tenant_ids = {row["tenant_id"] for row in data["tenants"]}
    property_ids = {row["property_id"] for row in data["properties"]}
    agreement_ids = {row["agreement_id"] for row in data["rental_agreements"]}
    agreements_by_id = {row["agreement_id"]: row for row in data["rental_agreements"]}

    for row_number, row in enumerate(data["properties"], start=1):
        if row["location_id"] not in location_ids:
            issues.append(
                ValidationIssue(
                    "properties", row_number, "ORPHAN_LOCATION", "location_id is not present"
                )
            )
        if row["owner_id"] not in owner_ids:
            issues.append(
                ValidationIssue("properties", row_number, "ORPHAN_OWNER", "owner_id is not present")
            )

    for row_number, row in enumerate(data["rental_agreements"], start=1):
        if row["property_id"] not in property_ids:
            issues.append(
                ValidationIssue(
                    "rental_agreements",
                    row_number,
                    "ORPHAN_PROPERTY",
                    "property_id is not present",
                )
            )
        if row["tenant_id"] not in tenant_ids:
            issues.append(
                ValidationIssue(
                    "rental_agreements",
                    row_number,
                    "ORPHAN_TENANT",
                    "tenant_id is not present",
                )
            )

    for row_number, row in enumerate(data["payments"], start=1):
        if row["agreement_id"] not in agreement_ids:
            issues.append(
                ValidationIssue(
                    "payments",
                    row_number,
                    "ORPHAN_AGREEMENT",
                    "agreement_id is not present",
                )
            )
            continue
        agreement = agreements_by_id[row["agreement_id"]]
        if not agreement["start_date"] <= row["due_date"] <= agreement["end_date"]:
            issues.append(
                ValidationIssue(
                    "payments",
                    row_number,
                    "PAYMENT_DUE_OUTSIDE_AGREEMENT",
                    "due_date must fall within the rental agreement",
                )
            )
    return issues


def validate_and_normalize(data: Dataset) -> Dataset:
    """Normalize a Stage 1 batch or fail it with actionable validation issues."""

    normalized, issues = _normalize_entities(data)
    issues.extend(_relationship_issues(normalized))
    if issues:
        raise DataValidationError(issues)
    return normalized
