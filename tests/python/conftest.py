"""Shared pytest setup for the FloodLens Python data-pipeline tests.

Makes the Airflow util package (``dags/utils``) and the standalone loader
script (``scripts/load_fema_data.py``) importable without installing the
project, and stubs ``psycopg2`` so ``db_client`` imports without the real
driver (individual tests monkeypatch ``db_client.psycopg2.connect``).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[2]

for rel in ("dags", "scripts"):
    path = str(REPO_ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

if "psycopg2" not in sys.modules:
    sys.modules["psycopg2"] = MagicMock(name="psycopg2")
