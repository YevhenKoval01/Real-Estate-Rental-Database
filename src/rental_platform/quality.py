import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from rental_platform.errors import RuleViolation
from rental_platform.types import ENTITY_ORDER, Dataset, Record
from rental_platform.validation import (
    IDENTIFIER_FIELDS,
    REQUIRED_FIELDS,
    normalize_record,
    relationship_issue,
    value_missing,
)

METADATA_FIELDS = {"batch_id", "source_timestamp", "record_fingerprint", "processed_at"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_batch_id(now: datetime | None = None) -> str:
    timestamp = now or utc_now()
    return f"batch-{timestamp.strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:8]}"


def _json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


def json_ready(record: Record) -> Record:
    return {key: _json_value(value) for key, value in record.items()}


def record_fingerprint(record: Record) -> str:
    business_values = {
        key: _json_value(value) for key, value in record.items() if key not in METADATA_FIELDS
    }
    canonical = json.dumps(
        business_values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RejectedRecord:
    record_type: str
    source_identifier: str
    batch_id: str
    reason_code: str
    explanation: str
    processed_at: datetime
    raw_record: Record

    def to_dict(self) -> Record:
        result = asdict(self)
        result["processed_at"] = self.processed_at.isoformat()
        result["raw_record"] = json_ready(self.raw_record)
        return result


@dataclass(frozen=True)
class QualityResult:
    accepted: Dataset
    rejected: tuple[RejectedRecord, ...]
    input_count: int

    @property
    def accepted_count(self) -> int:
        return sum(len(rows) for rows in self.accepted.values())

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def reason_counts(self) -> dict[str, int]:
        return dict(Counter(record.reason_code for record in self.rejected))


def _source_identifier(entity: str, row: Record, row_number: int) -> str:
    value = row.get(IDENTIFIER_FIELDS[entity])
    if value is None or not str(value).strip():
        return f"row-{row_number}"
    return str(value).strip()


def _rejection(
    entity: str,
    row: Record,
    row_number: int,
    batch_id: str,
    processed_at: datetime,
    code: str,
    explanation: str,
) -> RejectedRecord:
    return RejectedRecord(
        record_type=entity,
        source_identifier=_source_identifier(entity, row, row_number),
        batch_id=batch_id,
        reason_code=code,
        explanation=explanation,
        processed_at=processed_at,
        raw_record=row,
    )


def assess_quality(
    data: Dataset,
    *,
    batch_id: str,
    processed_at: datetime | None = None,
) -> QualityResult:
    """Apply record-level rules and return accepted and quarantined records."""

    processing_time = processed_at or utc_now()
    normalized: Dataset = {entity: [] for entity in ENTITY_ORDER}
    accepted_raw: dict[str, list[Record]] = {entity: [] for entity in ENTITY_ORDER}
    accepted_rows: dict[str, list[int]] = {entity: [] for entity in ENTITY_ORDER}
    rejected: list[RejectedRecord] = []

    for entity in ENTITY_ORDER:
        seen: set[str] = set()
        for row_number, row in enumerate(data[entity], start=1):
            missing = [field for field in REQUIRED_FIELDS[entity] if value_missing(row.get(field))]
            if missing:
                rejected.append(
                    _rejection(
                        entity,
                        row,
                        row_number,
                        batch_id,
                        processing_time,
                        "MISSING_REQUIRED_FIELD",
                        f"required value(s) missing: {', '.join(missing)}",
                    )
                )
                continue
            try:
                result = normalize_record(entity, row)
            except RuleViolation as exc:
                rejected.append(
                    _rejection(
                        entity,
                        row,
                        row_number,
                        batch_id,
                        processing_time,
                        exc.code,
                        str(exc),
                    )
                )
                continue

            identifier = str(result[IDENTIFIER_FIELDS[entity]])
            if identifier in seen:
                rejected.append(
                    _rejection(
                        entity,
                        row,
                        row_number,
                        batch_id,
                        processing_time,
                        "DUPLICATE_IDENTIFIER",
                        f"{IDENTIFIER_FIELDS[entity]} '{identifier}' occurs more than once",
                    )
                )
                continue
            seen.add(identifier)
            normalized[entity].append(result)
            accepted_raw[entity].append(row)
            accepted_rows[entity].append(row_number)

    for entity in ("properties", "rental_agreements", "payments"):
        kept_normalized = []
        kept_raw = []
        kept_rows = []
        for row, raw, row_number in zip(
            normalized[entity], accepted_raw[entity], accepted_rows[entity], strict=True
        ):
            issue = relationship_issue(entity, row, normalized)
            if issue:
                rejected.append(
                    _rejection(
                        entity,
                        raw,
                        row_number,
                        batch_id,
                        processing_time,
                        issue[0],
                        issue[1],
                    )
                )
            else:
                kept_normalized.append(row)
                kept_raw.append(raw)
                kept_rows.append(row_number)
        normalized[entity] = kept_normalized
        accepted_raw[entity] = kept_raw
        accepted_rows[entity] = kept_rows

    accepted: Dataset = {entity: [] for entity in ENTITY_ORDER}
    for entity in ENTITY_ORDER:
        for row in normalized[entity]:
            accepted[entity].append(
                {
                    **row,
                    "batch_id": batch_id,
                    "record_fingerprint": record_fingerprint(row),
                    "processed_at": processing_time,
                }
            )

    return QualityResult(
        accepted=accepted,
        rejected=tuple(rejected),
        input_count=sum(len(data[entity]) for entity in ENTITY_ORDER),
    )


def write_quality_artifacts(result: QualityResult, quality_path: Path, rejected_path: Path) -> None:
    batch_id = next(
        (record["batch_id"] for rows in result.accepted.values() for record in rows),
        result.rejected[0].batch_id if result.rejected else "unknown-batch",
    )
    quality_directory = quality_path / str(batch_id)
    rejected_directory = rejected_path / str(batch_id)
    quality_directory.mkdir(parents=True, exist_ok=True)
    rejected_directory.mkdir(parents=True, exist_ok=True)

    summary = {
        "batch_id": batch_id,
        "input_count": result.input_count,
        "accepted_count": result.accepted_count,
        "rejected_count": result.rejected_count,
        "reason_counts": result.reason_counts,
    }
    with (quality_directory / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")

    with (rejected_directory / "rejected_records.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as stream:
        for record in result.rejected:
            stream.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True))
            stream.write("\n")


def read_rejected_records(path: Path, batch_id: str) -> tuple[RejectedRecord, ...]:
    rejected_file = path / batch_id / "rejected_records.jsonl"
    if not rejected_file.is_file():
        return ()
    records = []
    with rejected_file.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            value = json.loads(line)
            records.append(
                RejectedRecord(
                    record_type=value["record_type"],
                    source_identifier=value["source_identifier"],
                    batch_id=value["batch_id"],
                    reason_code=value["reason_code"],
                    explanation=value["explanation"],
                    processed_at=datetime.fromisoformat(value["processed_at"]),
                    raw_record=value["raw_record"],
                )
            )
    return tuple(records)
