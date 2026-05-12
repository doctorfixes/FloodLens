"""
fema_client.py — FEMA REST API wrapper

Provides methods for querying the FEMA National Flood Hazard Layer (NFHL)
REST service to identify new or updated FIRM panels since the last refresh.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import requests

logger = logging.getLogger(__name__)

NFHL_REST_BASE = (
    "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer"
)

# Layer 28: S_FLD_HAZ_AR (Flood Hazard Areas)
FLOOD_ZONE_LAYER = 28

# Default page size for paginated requests
DEFAULT_PAGE_SIZE = 1000


class FemaClient:
    """Thin wrapper around the FEMA NFHL ArcGIS REST service."""

    def __init__(self, base_url: str = NFHL_REST_BASE, timeout: int = 30) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _query(
        self,
        layer: int,
        where: str = "1=1",
        out_fields: str = "*",
        result_offset: int = 0,
        result_record_count: int = DEFAULT_PAGE_SIZE,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a query against a specific NFHL layer."""
        url = f"{self.base_url}/{layer}/query"
        params: dict[str, Any] = {
            "where": where,
            "outFields": out_fields,
            "f": "json",
            "resultOffset": result_offset,
            "resultRecordCount": result_record_count,
            **kwargs,
        }
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(
                f"FEMA API error: {data['error'].get('message', data['error'])}"
            )
        return data

    def get_updated_panels(self, since: date) -> list[dict[str, Any]]:
        """
        Return FIRM panel records whose EFF_DATE is strictly after `since`.

        Parameters
        ----------
        since:
            Only panels with an effective date after this value are returned.

        Returns
        -------
        list[dict]
            Each dict contains at minimum ``DFIRM_ID`` and ``EFF_DATE``.
        """
        where = f"EFF_DATE > DATE '{since.isoformat()}'"
        records: list[dict[str, Any]] = []
        offset = 0

        while True:
            page = self._query(
                layer=FLOOD_ZONE_LAYER,
                where=where,
                out_fields="DFIRM_ID,EFF_DATE",
                result_offset=offset,
                result_record_count=DEFAULT_PAGE_SIZE,
            )
            features: list[dict[str, Any]] = page.get("features", [])
            records.extend(f["attributes"] for f in features)

            if len(features) < DEFAULT_PAGE_SIZE:
                break
            offset += DEFAULT_PAGE_SIZE

        logger.info(
            "Found %d updated FIRM panels since %s", len(records), since.isoformat()
        )
        return records

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "FemaClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
