from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from rental_platform.errors import DataValidationError, RuleViolation, ValidationIssue
from rental_platform.types import ENTITY_ORDER, Dataset, Record

REQUIRED_FIELDS = {
    "locations": ("location_id", "city", "region", "country_code", "source_timestamp"),
    "owners": ("owner_id", "full_name", "email", "source_timestamp"),
    "tenants": ("tenant_id", "full_name", "email", "source_timestamp"),
    "properties": (
        "property_id",
        "location_id",
        "owner_id",
        "property_type",
        "bedrooms",
        "size_sqm",
        "monthly_rent",
        "currency",
        "source_timestamp",
    ),
    "rental_agreements": (
        "agreement_id",
        "property_id",
        "tenant_id",
        "start_date",
        "end_date",
        "monthly_rent",
        "status",
        "source_timestamp",
    ),
    "payments": (
        "payment_id",
        "agreement_id",
        "due_date",
        "payment_date",
        "amount",
        "status",
        "source_timestamp",
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
        raise RuleViolation("INVALID_INTEGER", f"{field} must be an integer") from exc


def _decimal(value: object, field: str) -> Decimal:
    try:
        result = Decimal(_text(value)).quantize(Decimal("0.01"))
        if not result.is_finite():
            raise ValueError
        return result
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RuleViolation("INVALID_DECIMAL", f"{field} must be a finite decimal number") from exc


def _date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(_text(value))
    except (TypeError, ValueError) as exc:
        raise RuleViolation("INVALID_DATE", f"{field} must use ISO date format YYYY-MM-DD") from exc


def _timestamp(value: object) -> datetime:
    try:
        result = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise RuleViolation(
            "INVALID_SOURCE_TIMESTAMP", "source_timestamp must use ISO-8601 format"
        ) from exc
    if result.tzinfo is None:
        raise RuleViolation(
            "INVALID_SOURCE_TIMESTAMP", "source_timestamp must include a UTC offset"
        )
    return result


def _normalize_location(row: Record) -> Record:
    country_code = _text(row["country_code"]).upper()
    if len(country_code) != 2 or not country_code.isalpha():
        raise RuleViolation("INVALID_COUNTRY_CODE", "country_code must contain two letters")
    return {
        "location_id": _text(row["location_id"]),
        "city": _text(row["city"]).title(),
        "region": _text(row["region"]).title(),
        "country_code": country_code,
        "source_timestamp": _timestamp(row["source_timestamp"]),
    }


def _normalize_person(row: Record, identifier: str) -> Record:
    email = _text(row["email"]).lower()
    if "@" not in email:
        raise RuleViolation("INVALID_EMAIL", "email must contain an @ sign")
    return {
        identifier: _text(row[identifier]),
        "full_name": " ".join(_text(row["full_name"]).split()),
        "email": email,
        "source_timestamp": _timestamp(row["source_timestamp"]),
    }


def _normalize_property(row: Record) -> Record:
    size_sqm = _decimal(row["size_sqm"], "size_sqm")
    monthly_rent = _decimal(row["monthly_rent"], "monthly_rent")
    bedrooms = _integer(row["bedrooms"], "bedrooms")
    property_type = _text(row["property_type"]).lower()
    currency = _text(row["currency"]).upper()
    if not Decimal("0") < size_sqm <= Decimal("1000"):
        raise RuleViolation("INVALID_PROPERTY_SIZE", "size_sqm must be positive and at most 1000")
    if not Decimal("0") <= monthly_rent <= Decimal("100000"):
        raise RuleViolation("INVALID_RENT", "monthly_rent must be non-negative and at most 100000")
    if not 0 <= bedrooms <= 20:
        raise RuleViolation("INVALID_BEDROOM_COUNT", "bedrooms must be between 0 and 20")
    if property_type not in {"apartment", "house", "studio"}:
        raise RuleViolation("INVALID_PROPERTY_TYPE", "property_type is not supported")
    if currency not in {"PLN", "EUR", "USD"}:
        raise RuleViolation("INVALID_CURRENCY", "currency is not supported")
    return {
        "property_id": _text(row["property_id"]),
        "location_id": _text(row["location_id"]),
        "owner_id": _text(row["owner_id"]),
        "property_type": property_type,
        "bedrooms": bedrooms,
        "size_sqm": size_sqm,
        "monthly_rent": monthly_rent,
        "currency": currency,
        "source_timestamp": _timestamp(row["source_timestamp"]),
    }


def _normalize_agreement(row: Record) -> Record:
    start_date = _date(row["start_date"], "start_date")
    end_date = _date(row["end_date"], "end_date")
    monthly_rent = _decimal(row["monthly_rent"], "monthly_rent")
    status = _text(row["status"]).upper()
    if end_date < start_date:
        raise RuleViolation("INVALID_AGREEMENT_RANGE", "end_date must not be before start_date")
    if not Decimal("0") <= monthly_rent <= Decimal("100000"):
        raise RuleViolation("INVALID_RENT", "monthly_rent must be non-negative and at most 100000")
    if status not in {"ACTIVE", "EXPIRED", "TERMINATED"}:
        raise RuleViolation("INVALID_AGREEMENT_STATUS", "agreement status is not supported")
    return {
        "agreement_id": _text(row["agreement_id"]),
        "property_id": _text(row["property_id"]),
        "tenant_id": _text(row["tenant_id"]),
        "start_date": start_date,
        "end_date": end_date,
        "monthly_rent": monthly_rent,
        "status": status,
        "source_timestamp": _timestamp(row["source_timestamp"]),
    }


def _normalize_payment(row: Record) -> Record:
    amount = _decimal(row["amount"], "amount")
    status = _text(row["status"]).upper()
    if not Decimal("0") <= amount <= Decimal("1000000"):
        raise RuleViolation("INVALID_PAYMENT_AMOUNT", "amount must be between 0 and 1000000")
    if status not in {"PAID", "PENDING", "OVERDUE"}:
        raise RuleViolation("INVALID_PAYMENT_STATUS", "payment status is not supported")
    return {
        "payment_id": _text(row["payment_id"]),
        "agreement_id": _text(row["agreement_id"]),
        "due_date": _date(row["due_date"], "due_date"),
        "payment_date": _date(row["payment_date"], "payment_date"),
        "amount": amount,
        "status": status,
        "source_timestamp": _timestamp(row["source_timestamp"]),
    }


NORMALIZERS: dict[str, Callable[[Record], Record]] = {
    "locations": _normalize_location,
    "owners": lambda row: _normalize_person(row, "owner_id"),
    "tenants": lambda row: _normalize_person(row, "tenant_id"),
    "properties": _normalize_property,
    "rental_agreements": _normalize_agreement,
    "payments": _normalize_payment,
}


def value_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def normalize_record(entity: str, row: Record) -> Record:
    return NORMALIZERS[entity](row)


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
            missing = [field for field in REQUIRED_FIELDS[entity] if value_missing(row.get(field))]
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
                result = normalize_record(entity, row)
            except RuleViolation as exc:
                issues.append(ValidationIssue(entity, row_number, exc.code, str(exc)))
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


def relationship_issue(entity: str, row: Record, parents: Dataset) -> tuple[str, str] | None:
    if entity == "properties":
        if row["location_id"] not in {item["location_id"] for item in parents["locations"]}:
            return "ORPHAN_LOCATION", "location_id is not present"
        if row["owner_id"] not in {item["owner_id"] for item in parents["owners"]}:
            return "ORPHAN_OWNER", "owner_id is not present"
    elif entity == "rental_agreements":
        if row["property_id"] not in {item["property_id"] for item in parents["properties"]}:
            return "ORPHAN_PROPERTY", "property_id is not present"
        if row["tenant_id"] not in {item["tenant_id"] for item in parents["tenants"]}:
            return "ORPHAN_TENANT", "tenant_id is not present"
    elif entity == "payments":
        agreements = {item["agreement_id"]: item for item in parents["rental_agreements"]}
        agreement = agreements.get(row["agreement_id"])
        if agreement is None:
            return "ORPHAN_AGREEMENT", "agreement_id is not present"
        if not agreement["start_date"] <= row["due_date"] <= agreement["end_date"]:
            return (
                "PAYMENT_DUE_OUTSIDE_AGREEMENT",
                "due_date must fall within the rental agreement",
            )
    return None


def _relationship_issues(data: Dataset) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for entity in ("properties", "rental_agreements", "payments"):
        for row_number, row in enumerate(data[entity], start=1):
            issue = relationship_issue(entity, row, data)
            if issue:
                issues.append(ValidationIssue(entity, row_number, *issue))
    return issues


def validate_and_normalize(data: Dataset) -> Dataset:
    """Normalize a batch or fail it with actionable validation issues."""

    normalized, issues = _normalize_entities(data)
    issues.extend(_relationship_issues(normalized))
    if issues:
        raise DataValidationError(issues)
    return normalized
