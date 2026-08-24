import argparse
import logging
import os
from collections.abc import Sequence

from pydantic import ValidationError

from rental_platform.bronze import read_bronze
from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.generator import generate_source_data
from rental_platform.logging_config import configure_logging
from rental_platform.pipeline import run_pipeline
from rental_platform.validation import validate_and_normalize

LOGGER = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rental-platform",
        description="Rental Analytics & Data Engineering Platform",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "run"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--dataset-size", type=int)
        command_parser.add_argument("--seed", type=int)
    run_parser = subparsers.choices["run"]
    run_parser.add_argument(
        "--skip-load",
        action="store_true",
        help="create Bronze and Silver outputs without loading PostgreSQL",
    )
    subparsers.add_parser("validate")
    return parser


def _settings_from_arguments(arguments: argparse.Namespace) -> Settings:
    overrides = {}
    if getattr(arguments, "dataset_size", None) is not None:
        overrides["dataset_size"] = arguments.dataset_size
    if getattr(arguments, "seed", None) is not None:
        overrides["random_seed"] = arguments.seed
    return Settings(**overrides)


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging(os.getenv("RENTAL_LOG_LEVEL", "INFO").upper())
    arguments = _parser().parse_args(argv)
    try:
        settings = _settings_from_arguments(arguments)
        configure_logging(settings.log_level)
        if arguments.command == "generate":
            data = generate_source_data(settings)
            LOGGER.info(
                "Bronze generation completed path=%s records=%d",
                settings.bronze_path,
                sum(len(rows) for rows in data.values()),
            )
        elif arguments.command == "validate":
            data = validate_and_normalize(read_bronze(settings.bronze_path))
            LOGGER.info("Bronze validation passed records=%d", sum(map(len, data.values())))
        else:
            run_pipeline(settings, skip_load=arguments.skip_load)
        return 0
    except (PipelineError, ValidationError, OSError, ValueError) as exc:
        LOGGER.error("Command failed: %s", exc)
        return 1


def entrypoint() -> None:
    raise SystemExit(main())
