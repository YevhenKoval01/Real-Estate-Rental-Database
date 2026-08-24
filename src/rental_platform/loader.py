import logging
from collections.abc import Sequence

import psycopg

from rental_platform.config import Settings
from rental_platform.errors import PipelineError
from rental_platform.types import ENTITY_ORDER, Dataset

LOGGER = logging.getLogger(__name__)

LOAD_COLUMNS = {
    "locations": ("location_id", "city", "region", "country_code"),
    "owners": ("owner_id", "full_name", "email"),
    "tenants": ("tenant_id", "full_name", "email"),
    "properties": (
        "property_id",
        "location_id",
        "owner_id",
        "property_type",
        "bedrooms",
        "size_sqm",
        "monthly_rent",
        "currency",
    ),
    "rental_agreements": (
        "agreement_id",
        "property_id",
        "tenant_id",
        "start_date",
        "end_date",
        "monthly_rent",
        "status",
    ),
    "payments": (
        "payment_id",
        "agreement_id",
        "due_date",
        "payment_date",
        "amount",
        "status",
    ),
}


def _connect(settings: Settings) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        connect_timeout=10,
    )


def _row_values(row: dict[str, object], columns: Sequence[str]) -> tuple[object, ...]:
    return tuple(row[column] for column in columns)


def load_staging(data: Dataset, settings: Settings) -> dict[str, int]:
    """Replace Stage 1 staging tables in one transaction."""

    counts: dict[str, int] = {}
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('staging.locations')")
            if cursor.fetchone()[0] is None:
                raise PipelineError(
                    "PostgreSQL staging schema is missing; apply warehouse/migrations/"
                    "001_create_staging.sql"
                )

            cursor.execute(
                "TRUNCATE staging.payments, staging.rental_agreements, staging.properties, "
                "staging.tenants, staging.owners, staging.locations"
            )
            for entity in ENTITY_ORDER:
                columns = LOAD_COLUMNS[entity]
                placeholders = ", ".join(["%s"] * len(columns))
                statement = (
                    f"INSERT INTO staging.{entity} ({', '.join(columns)}) VALUES ({placeholders})"
                )
                cursor.executemany(
                    statement,
                    [_row_values(row, columns) for row in data[entity]],
                )
                counts[entity] = len(data[entity])
                LOGGER.info(
                    "Loaded PostgreSQL staging entity=%s records=%d", entity, counts[entity]
                )
        return counts
    except PipelineError:
        raise
    except psycopg.Error as exc:
        raise PipelineError(f"PostgreSQL staging load failed: {exc}") from exc


def read_staging_counts(settings: Settings) -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            for entity in ENTITY_ORDER:
                cursor.execute(f"SELECT count(*) FROM staging.{entity}")
                counts[entity] = int(cursor.fetchone()[0])
        return counts
    except psycopg.Error as exc:
        raise PipelineError(f"Could not read PostgreSQL staging counts: {exc}") from exc
