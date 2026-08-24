from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

pytest.importorskip("airflow")

from airflow.models import DagBag
from airflow.operators.bash import BashOperator

pytestmark = pytest.mark.airflow

DAG_FOLDER = Path(__file__).parents[2] / "airflow" / "dags"


@pytest.fixture(scope="module")
def dag_bag() -> DagBag:
    return DagBag(dag_folder=str(DAG_FOLDER), include_examples=False)


def test_dag_imports_without_errors(dag_bag: DagBag) -> None:
    assert dag_bag.import_errors == {}
    assert "rental_analytics_pipeline" in dag_bag.dags


def test_dag_has_the_real_pipeline_order(dag_bag: DagBag) -> None:
    dag = dag_bag.dags["rental_analytics_pipeline"]
    expected_order = [
        "generate",
        "ingest",
        "validate",
        "transform",
        "load",
        "dbt_build",
        "publish_run_summary",
    ]

    assert list(dag.task_dict) == expected_order
    for upstream, downstream in pairwise(expected_order):
        assert dag.get_task(upstream).downstream_task_ids == {downstream}


def test_tasks_execute_project_commands_and_limit_retries(dag_bag: DagBag) -> None:
    dag = dag_bag.dags["rental_analytics_pipeline"]
    expected_commands = {
        "generate": "rental-platform generate",
        "ingest": "rental-platform ingest",
        "validate": "rental-platform validate",
        "transform": "rental-platform transform",
        "load": "rental-platform load",
        "dbt_build": "dbt build",
        "publish_run_summary": "rental-platform summary",
    }

    for task_id, command in expected_commands.items():
        task = dag.get_task(task_id)
        assert isinstance(task, BashOperator)
        assert command in task.bash_command
        assert task.retries == (2 if task_id == "load" else 0)
