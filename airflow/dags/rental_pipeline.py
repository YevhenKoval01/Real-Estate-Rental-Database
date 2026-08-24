from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.operators.bash import BashOperator

from airflow import DAG

BATCH_ID = "{{ run_id | replace(':', '_') | replace('+', '_') }}"
BATCH_ENV = {"RENTAL_BATCH_ID": BATCH_ID}

with DAG(
    dag_id="rental_analytics_pipeline",
    description="Incremental Bronze-to-Gold rental analytics pipeline",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    default_args={"owner": "data-engineering", "retries": 0},
    tags=["rental", "analytics", "stage-2"],
) as dag:
    generate = BashOperator(
        task_id="generate",
        bash_command='rental-platform generate --batch-id "$RENTAL_BATCH_ID"',
        env=BATCH_ENV,
        append_env=True,
    )
    ingest = BashOperator(
        task_id="ingest",
        bash_command="rental-platform ingest",
    )
    validate = BashOperator(
        task_id="validate",
        bash_command='rental-platform validate --batch-id "$RENTAL_BATCH_ID"',
        env=BATCH_ENV,
        append_env=True,
    )
    transform = BashOperator(
        task_id="transform",
        bash_command='rental-platform transform --batch-id "$RENTAL_BATCH_ID"',
        env=BATCH_ENV,
        append_env=True,
    )
    load = BashOperator(
        task_id="load",
        bash_command='rental-platform load --batch-id "$RENTAL_BATCH_ID"',
        env=BATCH_ENV,
        append_env=True,
        retries=2,
        retry_delay=timedelta(minutes=1),
    )
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            "dbt build --project-dir /app/warehouse/dbt --profiles-dir /app/warehouse/dbt"
        ),
    )
    publish_run_summary = BashOperator(
        task_id="publish_run_summary",
        bash_command='rental-platform summary --batch-id "$RENTAL_BATCH_ID"',
        env=BATCH_ENV,
        append_env=True,
    )

    generate >> ingest >> validate >> transform >> load >> dbt_build >> publish_run_summary
