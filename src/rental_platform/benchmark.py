import json
import logging
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from rental_platform.config import Settings
from rental_platform.errors import PipelineError

LOGGER = logging.getLogger(__name__)

INDEXES = {
    "idx_payments_agreement_due_date": """
        CREATE INDEX IF NOT EXISTS idx_payments_agreement_due_date
        ON staging.payments (agreement_id, due_date)
        INCLUDE (payment_date, amount, status)
    """,
    "idx_properties_location": """
        CREATE INDEX IF NOT EXISTS idx_properties_location
        ON staging.properties (location_id, property_id)
    """,
    "idx_agreements_property_end_date": """
        CREATE INDEX IF NOT EXISTS idx_agreements_property_end_date
        ON staging.rental_agreements (property_id, end_date)
        INCLUDE (monthly_rent, status)
    """,
    "idx_agreements_active_end_date": """
        CREATE INDEX IF NOT EXISTS idx_agreements_active_end_date
        ON staging.rental_agreements (end_date)
        WHERE status = 'ACTIVE'
    """,
}

BENCHMARK_QUERY = """
SELECT payment_id, due_date, payment_date, amount, status
FROM staging.payments
WHERE agreement_id = %s
ORDER BY due_date
""".strip()


@dataclass(frozen=True)
class PlanMeasurement:
    median_execution_ms: float
    execution_ms: list[float]
    root_node: str
    plan: dict[str, object]


def _connect(settings: Settings) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        connect_timeout=10,
    )


def _set_indexes(settings: Settings, *, enabled: bool) -> None:
    with _connect(settings) as connection, connection.cursor() as cursor:
        for name, statement in INDEXES.items():
            if enabled:
                cursor.execute(statement)
            else:
                cursor.execute(f"DROP INDEX IF EXISTS staging.{name}")
        cursor.execute("ANALYZE staging.payments")
        cursor.execute("ANALYZE staging.rental_agreements")
        cursor.execute("ANALYZE staging.properties")


def _measure(settings: Settings, agreement_id: str, iterations: int) -> PlanMeasurement:
    measurements: list[float] = []
    final_plan: dict[str, object] | None = None
    with _connect(settings) as connection, connection.cursor() as cursor:
        for _ in range(2):
            cursor.execute(BENCHMARK_QUERY, (agreement_id,))
            cursor.fetchall()
        for _ in range(iterations):
            cursor.execute(
                f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {BENCHMARK_QUERY}",
                (agreement_id,),
            )
            raw = cursor.fetchone()[0]
            payload = raw[0] if isinstance(raw, list) else raw
            final_plan = payload
            measurements.append(float(payload["Execution Time"]))
    if final_plan is None:
        raise PipelineError("PostgreSQL returned no benchmark plan")
    return PlanMeasurement(
        median_execution_ms=round(statistics.median(measurements), 4),
        execution_ms=[round(value, 4) for value in measurements],
        root_node=str(final_plan["Plan"]["Node Type"]),
        plan=final_plan,
    )


def run_index_benchmark(
    settings: Settings,
    *,
    output_path: Path,
    iterations: int = 7,
) -> dict[str, object]:
    """Measure the same PostgreSQL query before and after the project indexes."""

    if not 3 <= iterations <= 50:
        raise ValueError("iterations must be between 3 and 50")
    try:
        with _connect(settings) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM staging.rental_agreements")
            agreement_count = int(cursor.fetchone()[0])
            cursor.execute("SELECT count(*) FROM staging.payments")
            payment_count = int(cursor.fetchone()[0])
        if agreement_count < 1 or payment_count < 1:
            raise PipelineError("Benchmark requires loaded rental agreements and payments")
        target_position = max(1, agreement_count * 9 // 10)
        agreement_id = f"AGR-{target_position:05d}"

        _set_indexes(settings, enabled=False)
        before = _measure(settings, agreement_id, iterations)
        _set_indexes(settings, enabled=True)
        after = _measure(settings, agreement_id, iterations)
    except psycopg.Error as exc:
        raise PipelineError(f"PostgreSQL benchmark failed: {exc}") from exc
    finally:
        try:
            _set_indexes(settings, enabled=True)
        except (PipelineError, psycopg.Error):
            LOGGER.exception("Could not restore benchmark indexes")

    improvement = (
        (before.median_execution_ms - after.median_execution_ms) / before.median_execution_ms * 100
        if before.median_execution_ms
        else 0.0
    )
    result: dict[str, object] = {
        "schema_version": 1,
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "dataset": {
            "rental_agreements": agreement_count,
            "payments": payment_count,
            "target_agreement_id": agreement_id,
        },
        "query": BENCHMARK_QUERY,
        "iterations": iterations,
        "before_indexes": asdict(before),
        "after_indexes": asdict(after),
        "median_change_percent": round(improvement, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    LOGGER.info(
        "Index benchmark completed agreements=%d payments=%d before_ms=%.4f after_ms=%.4f",
        agreement_count,
        payment_count,
        before.median_execution_ms,
        after.median_execution_ms,
    )
    return result
