# Portfolio and repository recommendations

## GitHub

Suggested description:

> Reproducible rental data platform with PySpark, PostgreSQL, dbt, Airflow, tested incremental loads, data-quality quarantine, Power BI TMDL, and measured SQL indexing.

Suggested topics:

`data-engineering`, `analytics-engineering`, `pyspark`, `postgresql`, `dbt`, `apache-airflow`, `power-bi`, `data-quality`, `dimensional-modeling`, `docker-compose`, `pytest`, `portfolio-project`

## CV

Title: **Rental Analytics & Data Engineering Platform — Python, PySpark, PostgreSQL, dbt, Airflow, Power BI**

Measured bullets:

- Built a deterministic Bronze/Silver/Gold rental pipeline with fingerprint-based incremental loading; verified an 81-record full load, a zero-insert replay, seven appended inserts, five targeted updates, and eight quarantined invalid rows.
- Designed and tested a dbt warehouse with 22 models, one SCD2 snapshot, six analytical marts, and 70 data tests; the verified build passed all 93 model/snapshot/test resources.
- Added query-driven PostgreSQL indexes and an 11-run `EXPLAIN ANALYZE` benchmark on 15,000 payments, reducing the measured median for the targeted drill-through query from 0.968 ms to 0.047 ms on the test machine.

These bullets intentionally describe local measured evidence rather than production scale, users, uptime, or revenue impact.
