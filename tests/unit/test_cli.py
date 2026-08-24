from pathlib import Path

from rental_platform.cli import main


def test_generate_command_returns_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RENTAL_BRONZE_PATH", str(tmp_path / "bronze"))

    assert main(["generate", "--dataset-size", "2", "--seed", "5"]) == 0
    assert (tmp_path / "bronze" / "properties.csv").is_file()


def test_invalid_dataset_size_returns_non_zero() -> None:
    assert main(["generate", "--dataset-size", "0"]) == 1
