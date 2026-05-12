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

NFHL_MAP_SERVER = "https://hazards.fema.gov/nfhl/rest/services/public/NFHL/MapServer"
FLOOD_HAZARD_LAYER_ID = 28
REQUEST_TIMEOUT = 30


def get_latest_eff_date(state_fips: str) -> str | None:
    """
    Returns the most recent panel effective date for a state from FEMA's
    NFHL REST service as an ISO date string, or None on failure.

    FEMA returns timestamps as epoch milliseconds.
    """
    url = f"{NFHL_MAP_SERVER}/{FLOOD_HAZARD_LAYER_ID}/query"
    params = {
        "where": f"STATE_FIPS='{state_fips}'",
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
