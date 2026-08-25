# Interview-ready design decisions

## Why PostgreSQL and dbt instead of rewriting the legacy SQL

The academic Oracle and SQL Server implementations demonstrate relational SQL, procedures, and triggers. PostgreSQL provides a reproducible open runtime for the new platform, while dbt separates transformation SQL, tests, lineage, and documentation from ingestion. Preserving both tells a clearer evolution story than deleting the original work.

## Why fingerprints and current-state staging

Stable business keys plus canonical SHA-256 fingerprints make retries cheap to explain: absent key inserts, changed fingerprint updates, equal fingerprint skips. Staging remains a current-state boundary because the simulated source has no tombstone contract. Property history belongs in the dbt snapshot, where SCD2 validity is explicit.

## Why shared Python quality rules before Spark output

One normalization/rule implementation is reused by tests and the Spark path, preventing rule drift at the current scale. Spark supplies typed input/output and Parquet. The tradeoff is driver collection; a genuinely distributed source would require Spark-native rules and partitioned loading.

## Why Airflow only retries load

Short database connectivity interruptions are transient, and fingerprint/upsert behavior makes load retries safe. Deterministic generation and validation failures need correction, not blind retries. Downstream summary publication is gated on dbt success.

## Why TMDL instead of PBIX

PBIX is binary and Power BI Desktop is unavailable in the verification environment. TMDL is reviewable, diffable, parameterized, and structurally testable. The project does not pretend that structural validation equals a Desktop refresh or rendered dashboard.

## Why a narrow benchmark

Indexes have write and storage costs. The project adds indexes only for observed join/filter patterns and measures a reproducible query before and after. Reporting the plan and raw timings makes the claim falsifiable instead of promising generic speedups.
