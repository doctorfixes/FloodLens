"""Shared pytest setup for the FloodLens Python data-pipeline tests.

Makes the Airflow util package (``dags/utils``) and the standalone loader
script (``scripts/load_fema_data.py``) importable without installing the
project, and stubs ``psycopg2`` so ``db_client`` imports without the real
driver (individual tests monkeypatch ``db_client.psycopg2.connect``).
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[2]

for rel in ("dags", "scripts"):
    path = str(REPO_ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

if "psycopg2" not in sys.modules:
    sys.modules["psycopg2"] = MagicMock(name="psycopg2")

# Stub Apache Airflow so the DAG module imports without the (heavy) real
# package. The DAG builds a `with DAG(...)` block and PythonOperators at import
# time; MagicMock supports the context-manager and call protocols they need.
if "airflow" not in sys.modules:
    airflow = types.ModuleType("airflow")
    airflow.DAG = MagicMock(name="DAG")
    sys.modules["airflow"] = airflow

    operators = types.ModuleType("airflow.operators")
    sys.modules["airflow.operators"] = operators

    python_ops = types.ModuleType("airflow.operators.python")
    python_ops.PythonOperator = MagicMock(name="PythonOperator")
    sys.modules["airflow.operators.python"] = python_ops

    models = types.ModuleType("airflow.models")
    # Variable.get(key, default_var=...) returns the provided default so the
    # DAG reads config from the environment, as it does in production.
    models.Variable = MagicMock(name="Variable")
    models.Variable.get = lambda key, default_var=None: default_var
    sys.modules["airflow.models"] = models
