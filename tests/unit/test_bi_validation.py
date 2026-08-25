from pathlib import Path

import pytest

from rental_platform.bi_validation import validate_semantic_model
from rental_platform.errors import PipelineError

ROOT = Path(__file__).parents[2]


def test_power_bi_semantic_model_contract_is_complete() -> None:
    result = validate_semantic_model(
        ROOT / "bi" / "Rental Analytics.SemanticModel",
        ROOT / "bi" / "semantic-model-contract.json",
    )

    assert result.table_count == 6
    assert result.measure_count == 6
    assert result.source_count == 6


def test_power_bi_validation_rejects_a_measure_contract_mismatch(tmp_path: Path) -> None:
    contract = tmp_path / "contract.json"
    contract.write_text(
        '{"sources": [{"table": "Missing", "relation": "analytics.missing"}], '
        '"measures": [{"table": "Missing", "name": "Missing"}]}',
        encoding="utf-8",
    )

    with pytest.raises(PipelineError, match="source contract mismatch"):
        validate_semantic_model(
            ROOT / "bi" / "Rental Analytics.SemanticModel",
            contract,
        )
