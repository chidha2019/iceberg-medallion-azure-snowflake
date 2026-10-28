"""Airflow DAG: bronze -> silver -> gold, one task per declared asset.

Task graph is derived from the asset registry so Airflow and lineage never drift.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from lakehouse import orchestrator
from lakehouse.config import Settings
from lakehouse.lineage import registry
from lakehouse.snowflake.connection import SnowflakeRunner

cfg = orchestrator.load_pipeline_config()
default_args = {"owner": "data-platform", "retries": cfg["retries"],
                "retry_delay": timedelta(seconds=cfg["retry_delay_seconds"])}


def _run(asset_name: str) -> None:
    s = Settings()
    r = SnowflakeRunner(s)
    a = registry.get(asset_name)
    if a.layer == "bronze":
        orchestrator.run_bronze(s, r, only=[asset_name.split(".", 1)[1]])
    else:
        a.fn(r, s)  # type: ignore[misc]


with DAG("lakehouse_medallion", schedule=cfg["schedule"], start_date=datetime(2026, 1, 1),
         catchup=False, default_args=default_args, tags=["lakehouse", "iceberg"]) as dag:
    tasks = {a.name: PythonOperator(task_id=a.name.replace(".", "__"),
                                    python_callable=_run, op_args=[a.name])
             for a in registry.all()}
    for upstream, downstream in registry.edges():
        if upstream in tasks:
            tasks[upstream] >> tasks[downstream]
