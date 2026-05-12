"""
nfhl_refresh_dag.py — Airflow quarterly delta refresh DAG

Orchestrates the quarterly update of FEMA National Flood Hazard Layer data:
1. Query FEMA REST API for panels updated since the last refresh.
2. Download updated NFHL shapefiles from FEMA MSC.
3. Run ogr2ogr ingestion into the flood_zones PostGIS table.

Schedule: Quarterly (first day of Jan, Apr, Jul, Oct at 02:00 UTC)
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from utils.db_client import DbClient
from utils.fema_client import FemaClient

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

default_args = {
    "owner": "floodlens",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def find_updated_panels(**context: object) -> list[str]:
    """Query FEMA for FIRM panels updated since the DB's max eff_date."""
    with DbClient() as db:
        last_date = db.get_max_eff_date()

    if last_date is None:
        # No data in DB yet — do a full load from an early sentinel date
        from datetime import date
        last_date = date(2000, 1, 1)
        logger.info("No existing data; performing full load since %s", last_date)
    else:
        logger.info("Fetching panels updated since %s", last_date)

    with FemaClient() as fema:
        panels = fema.get_updated_panels(since=last_date)

    # Deduplicate DFIRM IDs
    dfirm_ids = list({p["DFIRM_ID"] for p in panels if p.get("DFIRM_ID")})
    logger.info("Found %d unique FIRM panels to refresh", len(dfirm_ids))

    # Push to XCom for downstream tasks
    context["ti"].xcom_push(key="dfirm_ids", value=dfirm_ids)  # type: ignore[index]
    return dfirm_ids


def download_and_ingest(**context: object) -> None:
    """Download shapefiles for updated states and run ogr2ogr ingestion."""
    ti = context["ti"]  # type: ignore[index]
    dfirm_ids: list[str] = ti.xcom_pull(key="dfirm_ids", task_ids="find_updated_panels")

    if not dfirm_ids:
        logger.info("No updated panels; skipping download and ingest.")
        return

    # Extract unique state FIPS codes from DFIRM IDs (first 2 chars)
    state_fips_set = {dfirm_id[:2] for dfirm_id in dfirm_ids if len(dfirm_id) >= 2}
    logger.info("States to refresh: %s", sorted(state_fips_set))

    database_url = Variable.get("DATABASE_URL")

    # Build a subprocess environment that inherits the current environment
    # and injects the DATABASE_URL for the ingest script.
    import os
    subprocess_env = {**os.environ, "DATABASE_URL": database_url}

    for state_fips in sorted(state_fips_set):
        logger.info("Processing state FIPS %s", state_fips)

        # Download
        subprocess.run(
            [str(SCRIPTS_DIR / "download_nfhl.sh"), state_fips],
            check=True,
            text=True,
            env=subprocess_env,
        )

        # Ingest
        subprocess.run(
            [str(SCRIPTS_DIR / "ingest_nfhl.sh"), state_fips],
            check=True,
            text=True,
            env=subprocess_env,
        )

    logger.info("Refresh complete for states: %s", sorted(state_fips_set))


with DAG(
    dag_id="nfhl_quarterly_refresh",
    default_args=default_args,
    description="Quarterly delta refresh of FEMA NFHL flood zone data",
    schedule_interval="0 2 1 1,4,7,10 *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["floodlens", "nfhl", "fema"],
) as dag:
    t1 = PythonOperator(
        task_id="find_updated_panels",
        python_callable=find_updated_panels,
    )

    t2 = PythonOperator(
        task_id="download_and_ingest",
        python_callable=download_and_ingest,
    )

    t1 >> t2
