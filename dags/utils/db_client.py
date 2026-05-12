"""
db_client.py

Postgres utilities for the NFHL refresh DAG.
Handles eff_date comparison queries against the flood_zones table.
"""

from __future__ import annotations
import logging

import psycopg2

log = logging.getLogger(__name__)


def get_current_eff_date(state_fips: str, db_url: str) -> str | None:
    """
    Returns the most recent eff_date stored in flood_zones for the given
    state as an ISO date string, or None if the state has no rows.
    """
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "SELECT MAX(eff_date) FROM public.flood_zones WHERE state_fips = %s",
            (state_fips,),
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0].isoformat() if result and result[0] else None
    except Exception as exc:
        log.warning("DB eff_date query failed for state %s: %s", state_fips, exc)
        return None
