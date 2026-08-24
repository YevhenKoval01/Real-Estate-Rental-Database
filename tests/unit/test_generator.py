import hashlib
from pathlib import Path

from rental_platform.config import Settings
from rental_platform.generator import build_source_data, generate_source_data


def _directory_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(path.iterdir()):
        digest.update(file_path.name.encode())
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def test_generator_is_deterministic(tmp_path: Path) -> None:
    first_path = tmp_path / "first"
    second_path = tmp_path / "second"
    first = Settings(_env_file=None, bronze_path=first_path, dataset_size=8, random_seed=101)
    second = Settings(_env_file=None, bronze_path=second_path, dataset_size=8, random_seed=101)

    assert generate_source_data(first) == generate_source_data(second)
    assert _directory_digest(first_path) == _directory_digest(second_path)


def test_seed_changes_generated_values() -> None:
    assert build_source_data(5, 10) != build_source_data(5, 11)


def test_development_profile_has_stable_counts_and_relationships() -> None:
    data = build_source_data(12, 42)

    assert {entity: len(rows) for entity, rows in data.items()} == {
        "locations": 5,
        "owners": 4,
        "tenants": 12,
        "properties": 12,
        "rental_agreements": 12,
        "payments": 36,
    }
    property_ids = {row["property_id"] for row in data["properties"]}
    tenant_ids = {row["tenant_id"] for row in data["tenants"]}
    assert all(row["property_id"] in property_ids for row in data["rental_agreements"])
    assert all(row["tenant_id"] in tenant_ids for row in data["rental_agreements"])
