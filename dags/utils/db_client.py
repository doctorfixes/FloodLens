"""
db_client.py — Postgres connection and eff_date queries

Provides a thin helper class for connecting to the FloodLens Postgres
database and querying the latest effective date for a FIRM panel.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import date
from typing import Generator

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class DbClient:
    """Manages a Postgres connection and provides eff_date helpers."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.environ["DATABASE_URL"]
        self._conn: psycopg2.extensions.connection | None = None

    def connect(self) -> None:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                self.dsn,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            logger.debug("Connected to Postgres")

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.debug("Postgres connection closed")

    @contextmanager
    def cursor(self) -> Generator[psycopg2.extras.RealDictCursor, None, None]:
        self.connect()
        assert self._conn is not None
        with self._conn.cursor() as cur:
            yield cur
        self._conn.commit()

    def get_latest_eff_date(self, dfirm_id: str) -> date | None:
        """
        Return the latest effective date stored for the given FIRM panel ID,
        or None if no records exist yet.

        Parameters
        ----------
        dfirm_id:
            The DFIRM panel identifier (e.g. ``"48201C0095J"``).
        """
        sql = """
            SELECT MAX(eff_date) AS latest
            FROM flood_zones
            WHERE dfirm_id = %(dfirm_id)s
        """
        with self.cursor() as cur:
            cur.execute(sql, {"dfirm_id": dfirm_id})
            row = cur.fetchone()

        if row is None:
            return None
        return row["latest"]

    def get_max_eff_date(self) -> date | None:
        """Return the overall maximum effective date across all flood zones."""
        with self.cursor() as cur:
            cur.execute("SELECT MAX(eff_date) AS latest FROM flood_zones")
            row = cur.fetchone()
        if row is None:
            return None
        return row["latest"]

    def __enter__(self) -> "DbClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
