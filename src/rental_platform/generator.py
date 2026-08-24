import csv
import hashlib
import json
import random
import shutil
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.types import ENTITY_ORDER, Dataset

LOCATION_SEEDS = (
    ("Warsaw", "Masovian"),
    ("Krakow", "Lesser Poland"),
    ("Gdansk", "Pomeranian"),
    ("Wroclaw", "Lower Silesian"),
    ("Poznan", "Greater Poland"),
)
FIRST_NAMES = ("Anna", "Piotr", "Marta", "Jakub", "Zofia", "Tomasz", "Ewa", "Adam")
LAST_NAMES = ("Kowalski", "Nowak", "Wisniewski", "Zielinski", "Lewandowski")
PROPERTY_TYPES = ("apartment", "house", "studio")

CSV_ENTITIES = ("locations", "owners", "tenants", "properties", "rental_agreements")
SOURCE_FILES = {
    **{entity: f"{entity}.csv" for entity in CSV_ENTITIES},
    "payments": "payments.jsonl",
}
SOURCE_TIME_ORIGIN = datetime(2024, 1, 1, tzinfo=UTC)


def _person_name(rng: random.Random, index: int) -> str:
    first_name = FIRST_NAMES[(index + rng.randrange(len(FIRST_NAMES))) % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(index + rng.randrange(len(LAST_NAMES))) % len(LAST_NAMES)]
    return f"{first_name} {last_name}"


def _record_rng(seed: int, namespace: str, index: int) -> random.Random:
    """Return a stable per-record generator so larger batches preserve existing rows."""

    digest = hashlib.sha256(f"{seed}:{namespace}:{index}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], byteorder="big"))


def _inject_quality_issues(data: Dataset, issue_count: int) -> None:
    scenarios = (
        lambda: data["properties"].append(deepcopy(data["properties"][0])),
        lambda: data["tenants"].append(
            {
                **deepcopy(data["tenants"][0]),
                "tenant_id": "TEN-BAD-MISSING",
                "full_name": "",
            }
        ),
        lambda: data["payments"].append(
            {
                **deepcopy(data["payments"][0]),
                "payment_id": "PAY-BAD-DATE",
                "payment_date": "not-a-date",
            }
        ),
        lambda: data["rental_agreements"].append(
            {
                **deepcopy(data["rental_agreements"][0]),
                "agreement_id": "AGR-BAD-DATES",
                "end_date": "2023-12-31",
            }
        ),
        lambda: data["properties"].append(
            {
                **deepcopy(data["properties"][0]),
                "property_id": "PRP-BAD-SIZE",
                "size_sqm": "-5.00",
            }
        ),
        lambda: data["rental_agreements"].append(
            {
                **deepcopy(data["rental_agreements"][0]),
                "agreement_id": "AGR-BAD-RENT",
                "monthly_rent": "-100.00",
            }
        ),
        lambda: data["locations"][0].update({"city": "  WARSAW  ", "region": "masovian"}),
        lambda: data["properties"].append(
            {
                **deepcopy(data["properties"][0]),
                "property_id": "PRP-BAD-ORPHAN",
                "owner_id": "OWN-DOES-NOT-EXIST",
            }
        ),
        lambda: data["payments"].append(deepcopy(data["payments"][0])),
    )
    for scenario in scenarios[:issue_count]:
        scenario()


def _add_source_timestamps(data: Dataset) -> None:
    offset = 0
    for entity in ENTITY_ORDER:
        for row in data[entity]:
            row["source_timestamp"] = (SOURCE_TIME_ORIGIN + timedelta(seconds=offset)).isoformat()
            offset += 1


def build_source_data(
    dataset_size: int,
    seed: int,
    *,
    quality_issue_count: int = 0,
    rent_adjustment: Decimal = Decimal("0"),
) -> Dataset:
    """Build deterministic rental records and optionally inject known quality scenarios."""

    if dataset_size < 1:
        raise ValueError("dataset_size must be at least 1")
    if not 0 <= quality_issue_count <= 9:
        raise ValueError("quality_issue_count must be between 0 and 9")

    location_count = min(len(LOCATION_SEEDS), dataset_size)
    owner_count = min(5, max(1, (dataset_size + 2) // 3))

    locations = [
        {
            "location_id": f"LOC-{index + 1:03d}",
            "city": city,
            "region": region,
            "country_code": "PL",
        }
        for index, (city, region) in enumerate(LOCATION_SEEDS[:location_count])
    ]
    owners = [
        {
            "owner_id": f"OWN-{index + 1:04d}",
            "full_name": _person_name(_record_rng(seed, "owner", index), index),
            "email": f"owner{index + 1}@example.com",
        }
        for index in range(owner_count)
    ]
    tenants = [
        {
            "tenant_id": f"TEN-{index + 1:05d}",
            "full_name": _person_name(_record_rng(seed, "tenant", index), index),
            "email": f"tenant{index + 1}@example.com",
        }
        for index in range(dataset_size)
    ]

    properties = []
    agreements = []
    payments = []
    base_date = date(2024, 1, 1)

    for index in range(dataset_size):
        rng = _record_rng(seed, "property", index)
        property_id = f"PRP-{index + 1:05d}"
        agreement_id = f"AGR-{index + 1:05d}"
        property_type = PROPERTY_TYPES[rng.randrange(len(PROPERTY_TYPES))]
        bedrooms = 0 if property_type == "studio" else rng.randint(1, 4)
        size_sqm = rng.randint(28, 180)
        monthly_rent = Decimal(1100 + size_sqm * rng.randint(22, 36))
        if index == 0:
            monthly_rent += rent_adjustment
        start_date = base_date + timedelta(days=index * 11)
        end_date = start_date + timedelta(days=365)

        properties.append(
            {
                "property_id": property_id,
                "location_id": locations[index % location_count]["location_id"],
                "owner_id": owners[min(index // 3, owner_count - 1)]["owner_id"],
                "property_type": property_type,
                "bedrooms": bedrooms,
                "size_sqm": f"{size_sqm:.2f}",
                "monthly_rent": f"{monthly_rent:.2f}",
                "currency": "PLN",
            }
        )
        agreements.append(
            {
                "agreement_id": agreement_id,
                "property_id": property_id,
                "tenant_id": tenants[index]["tenant_id"],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "monthly_rent": f"{monthly_rent:.2f}",
                "status": "active",
            }
        )

        for payment_index in range(3):
            due_date = start_date + timedelta(days=30 * payment_index)
            payment_date = due_date + timedelta(days=rng.randint(0, 3))
            payments.append(
                {
                    "payment_id": f"PAY-{index + 1:05d}-{payment_index + 1:02d}",
                    "agreement_id": agreement_id,
                    "due_date": due_date.isoformat(),
                    "payment_date": payment_date.isoformat(),
                    "amount": f"{monthly_rent:.2f}",
                    "status": "paid",
                }
            )

    data: Dataset = {
        "locations": locations,
        "owners": owners,
        "tenants": tenants,
        "properties": properties,
        "rental_agreements": agreements,
        "payments": payments,
    }
    _inject_quality_issues(data, quality_issue_count)
    _add_source_timestamps(data)
    return data


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write an empty source file: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json_lines(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            stream.write("\n")


def write_source_data(data: Dataset, output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    for entity in CSV_ENTITIES:
        _write_csv(output_path / SOURCE_FILES[entity], data[entity])
    _write_json_lines(output_path / SOURCE_FILES["payments"], data["payments"])


def _configured_data(settings: Settings) -> Dataset:
    return build_source_data(
        settings.dataset_size,
        settings.random_seed,
        quality_issue_count=settings.quality_issue_count,
        rent_adjustment=settings.rent_adjustment,
    )


def generate_source_files(settings: Settings) -> Dataset:
    data = _configured_data(settings)
    write_source_data(data, settings.source_path)
    return data


def ingest_source_files(settings: Settings) -> None:
    settings.bronze_path.mkdir(parents=True, exist_ok=True)
    for file_name in SOURCE_FILES.values():
        source = settings.source_path / file_name
        if not source.is_file():
            raise PipelineError(f"Required source file does not exist: {source}")
        shutil.copyfile(source, settings.bronze_path / file_name)


def generate_source_data(settings: Settings) -> Dataset:
    """Stage 1-compatible helper that writes configured records directly to Bronze."""

    data = _configured_data(settings)
    write_source_data(data, settings.bronze_path)
    return data
