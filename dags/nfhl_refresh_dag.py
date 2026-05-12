"""
nfhl_refresh_dag.py

Quarterly FEMA NFHL delta refresh.

For each target state:
  1. Query FEMA REST for the latest panel effective date.
  2. Query the flood_zones table for the current stored effective date.
  3. If FEMA has newer data, download the state shapefile and re-ingest.
  4. If data is current, skip - no download, no ingestion, no table mutation.

The flood_zones table is never truncated. Row counts only ever increase.

Requirements:
  - Apache Airflow 2.x
  - ogr2ogr (GDAL >= 3.4) on the Airflow worker PATH
  - SUPABASE_DB_URL set as an Airflow Variable or environment variable
"""

from __future__ import annotations

import os
import subprocess
import logging
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

import requests

from utils.fema_client import get_latest_eff_date
from utils.db_client import get_current_eff_date

log = logging.getLogger(__name__)

# Pilot states. Expand incrementally as data layer is validated.
# FL, TX, CA, NY, LA - highest flood risk volume and broker activity.
TARGET_STATES: list[str] = ["12", "48", "06", "36", "22"]

DATA_DIR = Path("/tmp/floodlens_nfhl")
SCRIPT_PATH = Path("/opt/airflow/scripts/ingest_nfhl.sh")


def download_state_shapefile(state_fips: str) -> Path:
    """
    Downloads the NFHL state shapefile zip from FEMA MSC.
    Extracts and returns the path to S_FLD_HAZ_AR*.shp.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_DIR / f"NFHL_{state_fips}.zip"

    download_url = (
        f"https://msc.fema.gov/portal/downloadProduct"
        f"?productTypeID=NFHL&productSubTypeID=State&productVersionID={state_fips}"
    )

    log.info("Downloading NFHL shapefile for state %s", state_fips)
    res = requests.get(download_url, stream=True, timeout=300)
    res.raise_for_status()

    with open(zip_path, "wb") as f:
        for chunk in res.iter_content(chunk_size=8192):
            f.write(chunk)

    extract_dir = DATA_DIR / f"state_{state_fips}"
    extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    shp_files = list(extract_dir.rglob("S_FLD_HAZ_AR*.shp"))
    if not shp_files:
        raise FileNotFoundError(
            f"S_FLD_HAZ_AR .shp not found in NFHL zip for state {state_fips}"
        )

    log.info("Shapefile extracted: %s", shp_files[0])
    return shp_files[0]


def check_and_refresh(state_fips: str) -> None:
    """
    Main DAG task. Compares FEMA and DB effective dates.
    Triggers ingestion only when FEMA has newer data.
    """
    db_url = Variable.get(
        "SUPABASE_DB_URL",
        default_var=os.environ.get("SUPABASE_DB_URL", ""),
    )
    if not db_url:
        raise ValueError("SUPABASE_DB_URL not set in Airflow Variables or environment")

    fema_date = get_latest_eff_date(state_fips)
    db_date = get_current_eff_date(state_fips, db_url)

    log.info("State %s - FEMA: %s - DB: %s", state_fips, fema_date, db_date)

    if fema_date is None:
        log.warning("Cannot determine FEMA eff_date for state %s. Skipping.", state_fips)
        return

    if db_date and fema_date <= db_date:
        log.info("State %s is current. No ingestion needed.", state_fips)
        return

    log.info(
        "State %s has newer FEMA data. FEMA: %s > DB: %s. Starting ingestion.",
        state_fips,
        fema_date,
        db_date,
    )

    shp_path = download_state_shapefile(state_fips)

    result = subprocess.run(
        [str(SCRIPT_PATH), str(shp_path), state_fips],
        capture_output=True,
        text=True,
        env={**os.environ, "SUPABASE_DB_URL": db_url},
    )

    if result.returncode != 0:
        log.error("Ingestion script failed for state %s:\n%s", state_fips, result.stderr)
        raise RuntimeError(f"ingest_nfhl.sh exited non-zero for state {state_fips}")

    log.info("Ingestion complete for state %s", state_fips)


default_args = {
    "owner": "floodlens",
    "retries": 2,
    "retry_delay": timedelta(minutes=30),
    "email_on_failure": True,
}

with DAG(
    dag_id="nfhl_quarterly_refresh",
    description="Delta refresh FEMA NFHL data by state. Runs quarterly.",
    schedule_interval="0 2 1 1,4,7,10 *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["floodlens", "fema", "nfhl"],
) as dag:
    for fips in TARGET_STATES:
        PythonOperator(
            task_id=f"refresh_state_{fips}",
            python_callable=check_and_refresh,
            op_kwargs={"state_fips": fips},
        )
