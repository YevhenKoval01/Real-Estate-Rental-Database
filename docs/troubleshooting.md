# Troubleshooting

## Docker engine or PostgreSQL is unavailable

- Run `docker info` and start Docker Desktop/Engine if it cannot connect.
- Run `docker compose ps`; PostgreSQL must report `healthy`.
- Check port 5432 with `docker compose logs postgres`. Change `RENTAL_POSTGRES_PORT` if another service owns the host port.
- A migration is applied only when a new named volume is initialized. For an intentional local reset, run `docker compose down --volumes`, then start PostgreSQL again. This removes local project database data.

## Spark fails to start

The Docker image includes Java 17. A native local workflow must set `JAVA_HOME` to a Java 17 installation and make `java` available on `PATH`. On constrained machines, reduce `RENTAL_DATASET_SIZE`; the 5,000-property profile is optional.

## A repeated batch is not skipped

Confirm seed, dataset size, quality scenario count, and rent adjustment match. Fingerprints intentionally change when business values change. Inspect `record_fingerprint`, `batch_id`, and the latest `staging.pipeline_runs` row.

## dbt cannot connect or a test fails

Run `dbt debug --project-dir warehouse/dbt --profiles-dir warehouse/dbt`, confirm the `RENTAL_POSTGRES_*` environment values, then run `dbt build`. Do not publish BI data until the failing warehouse test is understood.

## Airflow does not show the DAG

Run `docker compose --profile airflow ps`, inspect `docker compose logs airflow`, and execute `airflow dags list-import-errors` inside the service. The first standalone startup can take about a minute. Local default credentials are not suitable beyond development.

## Power BI cannot load the model

Run `rental-platform validate-bi`, enable the Desktop TMDL preview feature, verify the semantic-model folder name and `byPath`, and confirm the six dbt source relations exist. PostgreSQL credentials are supplied interactively; they are not in TMDL.
