import json
import re
from dataclasses import dataclass
from pathlib import Path

from rental_platform.errors import PipelineError

MEASURE_PATTERN = re.compile(r"^\s*measure\s+'([^']+)'\s*=", re.MULTILINE)
TABLE_PATTERN = re.compile(r"^table\s+(?:'([^']+)'|([^\s]+))\s*$", re.MULTILINE)
RELATION_PATTERN = re.compile(r"\b(?:analytics|analytics_marts)\.[a-z_]+\b")
FORBIDDEN_SECRET_PATTERN = re.compile(
    r"(?:password|pwd)\s*=|postgresql://[^\s]+:[^\s]+@", re.IGNORECASE
)


@dataclass(frozen=True)
class BiValidationResult:
    table_count: int
    measure_count: int
    source_count: int


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Invalid Power BI JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PipelineError(f"Power BI JSON file must contain an object: {path}")
    return value


def _check_balanced(text: str, path: Path) -> None:
    for opening, closing in (("(", ")"), ("[", "]")):
        if text.count(opening) != text.count(closing):
            raise PipelineError(f"Unbalanced {opening}{closing} delimiters in {path}")


def validate_semantic_model(model_path: Path, contract_path: Path) -> BiValidationResult:
    """Validate the source-controlled PBIP/TMDL contract without Power BI Desktop."""

    definition = _read_json(model_path / "definition.pbism")
    if float(str(definition.get("version", "0"))) < 4.0:
        raise PipelineError("definition.pbism must use TMDL-capable version 4.0 or newer")

    contract = _read_json(contract_path)
    expected_sources = {
        str(item["table"]): str(item["relation"])
        for item in contract.get("sources", [])
        if isinstance(item, dict)
    }
    expected_measures = {
        (str(item["table"]), str(item["name"]))
        for item in contract.get("measures", [])
        if isinstance(item, dict)
    }
    if not expected_sources or not expected_measures:
        raise PipelineError("Power BI semantic-model contract has no sources or measures")

    definition_path = model_path / "definition"
    database_text = (definition_path / "database.tmdl").read_text(encoding="utf-8")
    model_text = (definition_path / "model.tmdl").read_text(encoding="utf-8")
    expressions_text = (definition_path / "expressions.tmdl").read_text(encoding="utf-8")
    if "compatibilityLevel: 1601" not in database_text:
        raise PipelineError("Power BI database must declare compatibility level 1601")
    if "defaultPowerBIDataSourceVersion: powerBI_V3" not in model_text:
        raise PipelineError("Power BI model must use the V3 data-source metadata format")
    if "DatabaseServer" not in expressions_text or "DatabaseName" not in expressions_text:
        raise PipelineError("Power BI connection parameters are missing")

    actual_measures: set[tuple[str, str]] = set()
    actual_sources: dict[str, str] = {}
    table_files = sorted((definition_path / "tables").glob("*.tmdl"))
    for table_file in table_files:
        text = table_file.read_text(encoding="utf-8")
        _check_balanced(text, table_file)
        if FORBIDDEN_SECRET_PATTERN.search(text):
            raise PipelineError(f"Credential-like value found in {table_file}")
        table_match = TABLE_PATTERN.search(text)
        if not table_match:
            raise PipelineError(f"TMDL table declaration is missing in {table_file}")
        table_name = table_match.group(1) or table_match.group(2)
        relations = set(RELATION_PATTERN.findall(text))
        expected_relation = expected_sources.get(table_name)
        if expected_relation is None:
            actual_sources[table_name] = sorted(relations)[0]
        elif expected_relation not in relations:
            raise PipelineError(
                f"Expected warehouse relation {expected_relation!r} in {table_file}, "
                f"found {relations}"
            )
        else:
            actual_sources[table_name] = expected_relation
        actual_measures.update((table_name, name) for name in MEASURE_PATTERN.findall(text))
        if "partition " not in text or "mode: import" not in text:
            raise PipelineError(f"Import partition is missing in {table_file}")

    if actual_sources != expected_sources:
        raise PipelineError(
            f"Power BI source contract mismatch: expected {expected_sources}, got {actual_sources}"
        )
    if actual_measures != expected_measures:
        raise PipelineError(
            "Power BI measure contract mismatch: "
            f"expected {expected_measures}, got {actual_measures}"
        )
    return BiValidationResult(
        table_count=len(actual_sources),
        measure_count=len(actual_measures),
        source_count=len(set(actual_sources.values())),
    )
