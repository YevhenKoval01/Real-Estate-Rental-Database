# Testing strategy

Tests follow the layer where a failure can be diagnosed most cheaply:

- Unit tests cover configuration, deterministic and extension-stable generation, normalization, rejection reasons, fingerprints, CLI exit behavior, BI contract validation, and benchmark safeguards.
- PostgreSQL integration tests cover full/new/changed/unchanged loading, audit reconciliation, quarantine persistence, failed-run recording, and safe recovery with the same batch ID.
- The PySpark end-to-end test verifies source and Bronze files, Silver Parquet, PostgreSQL loading, and an identical replay. It requires Java 17 and PostgreSQL.
- dbt's 70 tests cover uniqueness, nullability, relationships, accepted values, financial/date invariants, and occupancy bounds across 22 models plus one snapshot.
- Airflow tests parse the DAG, verify the exact seven-task order, commands, and retry boundary.
- The Compose smoke command runs five deterministic batches, two dbt builds, snapshot history checks, quarantine checks, and BI validation from a clean database.

CI separates the dbt/PySpark environment from the Airflow environment because their transitive dependency constraints differ. The `quality` workflow runs code, package, PostgreSQL, dbt, and pytest gates; `docker-smoke` proves the documented container path and uploads machine-readable smoke evidence.

Generated data, dbt targets, package artifacts, evidence JSON, logs, and database volumes are ignored. Tests may recreate only the project's known development schemas and tables.
