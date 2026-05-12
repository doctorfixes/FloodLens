"""
fema_client.py

Thin wrapper around FEMA's NFHL ArcGIS REST service.
Used by the DAG to compare effective dates before triggering ingestion.
"""

from __future__ import annotations
import logging
from datetime import datetime

import requests

log = logging.getLogger(__name__)

NFHL_MAP_SERVER = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
FIRM_PANEL_LAYER_ID = 3
REQUEST_TIMEOUT = 30


def get_latest_eff_date(state_fips: str) -> str | None:
    """
    Returns the most recent panel effective date for a state from FEMA's
    NFHL FIRM Panels layer as an ISO date string, or None on failure.

    FEMA returns timestamps as epoch milliseconds.
    """
    url = f"{NFHL_MAP_SERVER}/{FIRM_PANEL_LAYER_ID}/query"
    params = {
        # FEMA uses 9999-09-09 on some not-printed panels. Exclude future
        # placeholders so the DAG does not re-ingest forever.
        "where": f"ST_FIPS='{state_fips}' AND EFF_DATE < CURRENT_TIMESTAMP",
        "outFields": "EFF_DATE",
        "returnGeometry": "false",
        "orderByFields": "EFF_DATE DESC",
        "resultRecordCount": 1,
        "f": "json",
    }

    try:
        res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        features = res.json().get("features", [])
        if not features:
            log.warning("No FEMA features returned for state %s", state_fips)
            return None
        raw_ts = features[0]["attributes"]["EFF_DATE"]
        return datetime.utcfromtimestamp(raw_ts / 1000).strftime("%Y-%m-%d")
    except Exception as exc:
        log.warning("FEMA eff_date fetch failed for state %s: %s", state_fips, exc)
        return None
