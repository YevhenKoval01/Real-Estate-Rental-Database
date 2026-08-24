import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from rental_platform.config import Settings
from rental_platform.types import Dataset

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


def _person_name(rng: random.Random, index: int) -> str:
    first_name = FIRST_NAMES[(index + rng.randrange(len(FIRST_NAMES))) % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(index + rng.randrange(len(LAST_NAMES))) % len(LAST_NAMES)]
    return f"{first_name} {last_name}"


def build_source_data(dataset_size: int, seed: int) -> Dataset:
    """Build a deterministic, internally consistent Stage 1 source batch."""

    if dataset_size < 1:
        raise ValueError("dataset_size must be at least 1")

    rng = random.Random(seed)
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
            "full_name": _person_name(rng, index),
            "email": f"owner{index + 1}@example.com",
        }
        for index in range(owner_count)
    ]
    tenants = [
        {
            "tenant_id": f"TEN-{index + 1:05d}",
            "full_name": _person_name(rng, index + owner_count),
            "email": f"tenant{index + 1}@example.com",
        }
        for index in range(dataset_size)
    ]

    properties = []
    agreements = []
    payments = []
    base_date = date(2024, 1, 1)

    for index in range(dataset_size):
        property_id = f"PRP-{index + 1:05d}"
        agreement_id = f"AGR-{index + 1:05d}"
        property_type = PROPERTY_TYPES[rng.randrange(len(PROPERTY_TYPES))]
        bedrooms = 0 if property_type == "studio" else rng.randint(1, 4)
        size_sqm = rng.randint(28, 180)
        monthly_rent = 1100 + size_sqm * rng.randint(22, 36)
        start_date = base_date + timedelta(days=index * 11)
        end_date = start_date + timedelta(days=365)

        properties.append(
            {
                "property_id": property_id,
                "location_id": locations[index % location_count]["location_id"],
                "owner_id": owners[index % owner_count]["owner_id"],
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

    return {
        "locations": locations,
        "owners": owners,
        "tenants": tenants,
        "properties": properties,
        "rental_agreements": agreements,
        "payments": payments,
    }


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


def write_source_data(data: Dataset, bronze_path: Path) -> None:
    bronze_path.mkdir(parents=True, exist_ok=True)
    for entity in CSV_ENTITIES:
        _write_csv(bronze_path / f"{entity}.csv", data[entity])
    _write_json_lines(bronze_path / "payments.jsonl", data["payments"])


def generate_source_data(settings: Settings) -> Dataset:
    data = build_source_data(settings.dataset_size, settings.random_seed)
    write_source_data(data, settings.bronze_path)
    return data
