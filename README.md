# Rental Analytics & Data Engineering Platform

A reproducible portfolio platform that turns imperfect rental source records into typed Parquet, auditable incremental PostgreSQL state, a tested dbt dimensional warehouse, business marts, and a source-controlled Power BI semantic model. It evolves a third-semester database assignment without deleting its original SQL Server or Oracle implementation.

## Business problem

Rental operations need trustworthy answers to basic questions—occupancy, collected revenue, overdue payments, rent per square metre, expiring agreements, and location trends—but source extracts can contain duplicate IDs, broken dates, impossible values, and missing relationships. This project demonstrates how to make those answers reproducible, reject bad records explicitly, replay batches safely, retain selected history, and expose tested measures to BI.

## Architecture

```mermaid
flowchart LR
    SRC[Deterministic synthetic source] --> B[Bronze CSV / JSONL]
    B --> Q{PySpark validation}
    Q -->|accepted| S[Silver Parquet]
    Q -->|rejected| R[JSONL quarantine]
    S --> PG[(PostgreSQL staging)]
    R --> PG
    PG --> DBT[dbt Gold star schema]
    DBT --> MARTS[Analytical marts]
    MARTS --> BI[Power BI TMDL]
    AF[Airflow] -. orchestrates seven steps .-> SRC
    AF -.-> DBT
```

See [platform architecture](docs/architecture.md), [lineage](docs/lineage.md), and the [data dictionary](docs/data-dictionary.md).

## Technology choices

| Technology | Responsibility |
|---|---|
| Python 3.12 | typed configuration, deterministic generation, shared quality rules, incremental loader, CLI, logging, benchmark and smoke runner |
| PySpark 3.5.9 | Bronze reading, typed normalization, Silver Parquet writing |
| PostgreSQL 16.10 | canonical current-state staging, audit/rejection storage, analytical runtime |
| dbt Core 1.11.14 / dbt-postgres 1.11.0 | staging/intermediate SQL, Gold dimensions/facts, marts, SCD2 snapshot, 70 data tests |
| Airflow 2.11.2 | optional seven-task orchestration with retries only at the transient database boundary |
| Power BI TMDL | source-controlled, parameterized semantic model with six DAX measures |
| Docker Compose | reproducible PostgreSQL, pipeline, dbt, Airflow and smoke environments |
| pytest / Ruff / GitHub Actions | unit, integration, E2E, DAG, semantic-model and container quality gates |

No Kafka, Kubernetes, web frontend, or fabricated cloud integration is included; each dependency has a direct data-platform responsibility.

## Key capabilities

- Fixed-seed, extension-stable generation for locations, owners, tenants, properties, agreements, and payments.
- Nine deterministic bad-data scenarios covering duplicates, missing fields, invalid dates/ranges, impossible size/rent, inconsistent location text, and orphaned keys.
- Record-level quarantine with batch, source identity, reason code, readable explanation, raw JSON, and UTC processing time.
- Canonical SHA-256 fingerprints: new keys insert, changed business values update, unchanged rows skip.
- Transactional loads, idempotent rejection upserts, auditable failed runs, and safe recovery using the same batch ID.
- Five dimensions, three facts, six marts, and a property-attribute SCD Type 2 snapshot.
- Structured JSON operational logs and clear exit codes: `0` success, `1` expected/configuration/pipeline failure, `2` unexpected failure.
- Query-driven PostgreSQL indexes plus a reproducible JSON `EXPLAIN ANALYZE` benchmark.
- Source-controlled TMDL with measures for occupancy, revenue, rent per square metre, overdue rate, expiring agreements, and location rent trend.

## Bronze, Silver and Gold

- **Source/Bronze:** CSV and JSON Lines preserve source-shaped strings. Ingest copies the current extract without business mutation.
- **Silver:** shared rules normalize harmless text differences, type valid values, write accepted entities to Parquet, and partition quality/rejection evidence by batch.
- **Staging:** PostgreSQL retains current accepted business state plus fingerprints, batch metadata, pipeline runs, and rejection history.
- **Gold:** dbt resolves joins and builds `dim_date`, `dim_location`, `dim_property`, `dim_owner`, `dim_tenant`, `fact_rental_agreement`, `fact_payment`, and daily-grain `fact_occupancy`.
- **Marts/BI:** six views expose occupancy, monthly revenue, overdue payments, rent/m², upcoming expirations, and location trends. TMDL adds explicit DAX measures.

The source has no tombstone contract, so a missing row does not delete staging data. Property price/attribute changes are versioned by `analytics_snapshots.property_history`; other dimensions/facts rebuild deterministically. Details are in [incremental processing](docs/incremental-processing.md).

## Fresh-clone quickstart

Requirements: Docker Engine/Desktop with Compose and Git. The images provide Python, Java, Spark and dbt.

```powershell
git clone https://github.com/YevhenKoval01/Real-Estate-Rental-Database.git
Set-Location Real-Estate-Rental-Database
Copy-Item .env.example .env

docker compose --profile pipeline --profile airflow --profile smoke config --quiet
docker compose up --detach --wait postgres

docker compose --profile pipeline run --build --rm pipeline run --batch-id quickstart-full
docker compose --profile pipeline run --rm dbt
docker compose --profile pipeline run --rm pipeline validate-bi

docker compose exec postgres psql -U rental -d rental_analytics -c "SELECT batch_id, input_count, accepted_count, rejected_count, inserted_count, updated_count, skipped_count, final_status FROM staging.pipeline_runs ORDER BY started_at DESC LIMIT 1;"
```

The first initialization applies every numbered file in `warehouse/migrations`. Repeating with a different batch ID should skip all 81 unchanged default records:

```powershell
docker compose --profile pipeline run --rm pipeline run --batch-id quickstart-identical
```

Exercise append, change, and quarantine behavior:

```powershell
docker compose --profile pipeline run --rm pipeline run --batch-id quickstart-new --dataset-size 13
docker compose --profile pipeline run --rm pipeline run --batch-id quickstart-changed --dataset-size 13 --rent-adjustment 250
docker compose --profile pipeline run --rm pipeline run --batch-id quickstart-invalid --dataset-size 13 --rent-adjustment 250 --quality-issues 9
docker compose --profile pipeline run --rm dbt
```

Use `docker compose down` to preserve the database. `docker compose down --volumes` is an intentional destructive reset of this project's local PostgreSQL volume.

## One-command complete smoke test

The smoke profile resets only the known project schemas/tables, then runs full, identical, new, changed, and invalid batches; two dbt builds; SCD2 checks; rejection reconciliation; and BI validation.

```powershell
docker compose down --volumes
docker compose --profile smoke run --build --rm smoke
Get-Content data/benchmark/smoke-evidence.json
```

The evidence file is generated and intentionally ignored by Git.

## Airflow

The optional DAG is:

```text
generate -> ingest -> validate -> transform -> load -> dbt_build -> publish_run_summary
```

```powershell
docker compose --profile airflow up --build --detach --wait airflow
docker compose --profile airflow ps
docker compose exec airflow airflow dags list --output table
```

Open `http://localhost:8080` and use the development account from `.env`. Only `load` retries—twice, one minute apart—because short PostgreSQL outages are transient and the load is idempotent. See [orchestration](docs/orchestration.md).

## Power BI

`bi/Rental Analytics.SemanticModel` is a TMDL semantic model, not a fabricated `.pbix`. The automated validator passed six subject tables, six required measures, and six primary warehouse sources:

```powershell
docker compose --profile pipeline run --rm pipeline validate-bi
```

Power BI Desktop was unavailable, so Desktop parsing, refresh, DAX execution, report rendering, and publication are not claimed. Follow the exact [Power BI import and refresh instructions](docs/power-bi.md) to create a local PBIP report around the supplied semantic model. No misleading dashboard screenshot is included.

## Performance profile

The optional profile keeps CI small while allowing a 5,000-property local load:

```powershell
docker compose down --volumes
docker compose --env-file config/performance.env.example up --detach --wait postgres
docker compose --env-file config/performance.env.example --profile pipeline run --build --rm pipeline run --batch-id performance-5000
docker compose --env-file config/performance.env.example --profile pipeline run --rm pipeline benchmark --iterations 11
Get-Content data/benchmark/index-benchmark.json
```

Measured on the documented development machine with 5,000 agreements and 15,000 payments, the targeted drill-through query changed from a 0.968 ms sequential-scan/sort median to a 0.047 ms index-scan median across 11 warm executions (95.14% lower for that query). This is a narrow microbenchmark, not a general performance guarantee. Full plans, caveats, environment, and method are in the [performance report](docs/performance.md).

## Local Python development

Use Python 3.12 and Java 17; PostgreSQL can remain in Docker. Keep Airflow in a separate environment if your resolver reports transitive conflicts with dbt.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install --editable ".[dev,warehouse]"
docker compose up --detach --wait postgres

$env:RENTAL_TEST_POSTGRES_DSN="postgresql://rental:rental_dev@localhost:5432/rental_analytics"
$env:SPARK_LOCAL_IP="127.0.0.1"
.venv\Scripts\rental-platform run --batch-id local-full
.venv\Scripts\dbt build --project-dir warehouse/dbt --profiles-dir warehouse/dbt
.venv\Scripts\rental-platform validate-bi
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\pytest --ignore=tests/airflow
```

Install `.[dev,orchestration]` in a separate virtual environment and run `pytest tests/airflow` for isolated DAG validation. Individual CLI commands are `generate`, `ingest`, `validate`, `transform`, `load`, `summary`, `validate-bi`, `benchmark`, `run`, and `smoke`.

## Verified results

Final clean smoke evidence on 2026-08-25:

| Batch | Input | Accepted | Rejected | Inserted | Updated | Skipped |
|---|---:|---:|---:|---:|---:|---:|
| full | 81 | 81 | 0 | 81 | 0 | 0 |
| identical | 81 | 81 | 0 | 0 | 0 | 81 |
| new | 88 | 88 | 0 | 7 | 0 | 81 |
| changed | 88 | 88 | 0 | 0 | 5 | 83 |
| invalid | 96 | 88 | 8 | 0 | 0 | 88 |

- Rejections: 8 records across 7 reason codes.
- Snapshot: 14 rows for 13 current properties; `PRP-00001` has 2 versions.
- dbt: 22 models, 1 snapshot, 70 data tests; `PASS=93 WARN=0 ERROR=0 SKIP=0` in both smoke builds.
- Power BI structural validation: 6 tables, 6 measures, 6 primary sources.
- pytest, Ruff, package, Compose, container dependency, DAG, clean smoke, and legacy-preservation results are documented in [testing strategy](docs/testing-strategy.md).

## Repository structure

```text
.
|-- airflow/dags/                  # optional orchestration
|-- bi/                            # TMDL model and machine-readable measure contract
|-- config/                        # optional performance profile
|-- docker/                        # pinned pipeline and isolated Airflow images
|-- docs/                          # architecture, operations, evidence and legacy assets
|-- scripts/                       # retained local verification helper
|-- sql/oracle/                    # preserved academic Oracle implementation
|-- sql/sql-server/                # preserved academic SQL Server implementation
|-- src/rental_platform/           # generator, quality, Spark, loader, CLI and verification
|-- tests/                         # unit, integration, E2E and DAG tests
|-- warehouse/dbt/                 # 22 models, snapshot and 70 tests
|-- warehouse/migrations/          # versioned staging, audit and index DDL
|-- compose.yaml
|-- pyproject.toml
`-- LICENSE
```

## Documentation

- [Architecture and dimensional model](docs/architecture.md)
- [Data dictionary](docs/data-dictionary.md)
- [Data quality and measured rejection report](docs/data-quality.md)
- [Incremental/idempotent behavior](docs/incremental-processing.md)
- [Airflow orchestration](docs/orchestration.md)
- [Power BI model and import](docs/power-bi.md)
- [Performance benchmark](docs/performance.md)
- [Testing strategy](docs/testing-strategy.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Design decisions](docs/design-decisions.md)
- [Limitations](docs/limitations.md) and [roadmap](docs/roadmap.md)
- [GitHub/CV recommendations](docs/portfolio.md)

## Original academic project

The repository began as a third-semester relational database assignment written in Polish. Its SQL Server and Oracle schemas, seed data, analytical queries, procedures, triggers, ER diagrams, and original requirements remain under `sql/` and `docs/`. They are clearly treated as educational/legacy assets rather than PostgreSQL migrations.

![Original SQL Server entity-relationship diagram](docs/diagrams/sql-server-erd.png)

## Status and limitations

All three planned stages are implemented. The default workflow is designed for a normal student computer, and heavyweight orchestration remains optional. Important boundaries remain: synthetic rather than external sources, no inferred deletions, driver-collected quality evaluation, local Airflow topology, TMDL structural rather than Desktop verification, and a query-specific performance result. See [known limitations](docs/limitations.md) before reusing the design.

Licensed under the [MIT License](LICENSE).
