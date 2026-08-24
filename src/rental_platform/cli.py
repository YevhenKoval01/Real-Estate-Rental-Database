import argparse
import logging
import os
from collections.abc import Sequence
from decimal import Decimal

from pydantic import ValidationError

from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.generator import generate_source_files, ingest_source_files
from rental_platform.logging_config import configure_logging
from rental_platform.pipeline import (
    load_silver_batch,
    publish_run_summary,
    run_pipeline,
    validate_bronze_batch,
)
from rental_platform.quality import create_batch_id
from rental_platform.spark_pipeline import transform_bronze_to_silver

LOGGER = logging.getLogger(__name__)


def _add_profile_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dataset-size", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--quality-issues", type=int)
    parser.add_argument("--rent-adjustment", type=Decimal)


def _add_batch_argument(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    parser.add_argument("--batch-id", required=required)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rental-platform",
        description="Rental Analytics & Data Engineering Platform",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate")
    _add_profile_arguments(generate_parser)
    _add_batch_argument(generate_parser)

    subparsers.add_parser("ingest")

    validate_parser = subparsers.add_parser("validate")
    _add_batch_argument(validate_parser)

    transform_parser = subparsers.add_parser("transform")
    _add_batch_argument(transform_parser)

    load_parser = subparsers.add_parser("load")
    _add_batch_argument(load_parser, required=True)

    run_parser = subparsers.add_parser("run")
    _add_profile_arguments(run_parser)
    _add_batch_argument(run_parser)
    run_parser.add_argument(
        "--skip-load",
        action="store_true",
        help="create source, Bronze, quality, and Silver outputs without loading PostgreSQL",
    )

    summary_parser = subparsers.add_parser("summary")
    _add_batch_argument(summary_parser, required=True)
    return parser


def _settings_from_arguments(arguments: argparse.Namespace) -> Settings:
    overrides = {}
    if getattr(arguments, "dataset_size", None) is not None:
        overrides["dataset_size"] = arguments.dataset_size
    if getattr(arguments, "seed", None) is not None:
        overrides["random_seed"] = arguments.seed
    if getattr(arguments, "quality_issues", None) is not None:
        overrides["quality_issue_count"] = arguments.quality_issues
    if getattr(arguments, "rent_adjustment", None) is not None:
        overrides["rent_adjustment"] = arguments.rent_adjustment
    return Settings(**overrides)


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging(os.getenv("RENTAL_LOG_LEVEL", "INFO").upper())
    arguments = _parser().parse_args(argv)
    try:
        settings = _settings_from_arguments(arguments)
        configure_logging(settings.log_level)
        batch_id = getattr(arguments, "batch_id", None) or create_batch_id()
        if arguments.command == "generate":
            data = generate_source_files(settings)
            ingest_source_files(settings)
            LOGGER.info(
                "Source generation completed batch_id=%s path=%s records=%d",
                batch_id,
                settings.source_path,
                sum(len(rows) for rows in data.values()),
            )
        elif arguments.command == "ingest":
            ingest_source_files(settings)
            LOGGER.info("Source ingestion completed path=%s", settings.bronze_path)
        elif arguments.command == "validate":
            validate_bronze_batch(settings, batch_id)
        elif arguments.command == "transform":
            transform_bronze_to_silver(settings, batch_id=batch_id)
        elif arguments.command == "load":
            load_silver_batch(settings, batch_id)
        elif arguments.command == "summary":
            publish_run_summary(settings, batch_id)
        else:
            run_pipeline(
                settings,
                batch_id=batch_id,
                skip_load=arguments.skip_load,
            )
        return 0
    except (PipelineError, ValidationError, OSError, ValueError) as exc:
        LOGGER.error("Command failed: %s", exc)
        return 1


def entrypoint() -> None:
    raise SystemExit(main())
