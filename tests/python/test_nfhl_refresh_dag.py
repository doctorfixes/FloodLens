"""Tests for the NFHL refresh DAG's check_and_refresh decision logic.

Airflow is stubbed in conftest.py so the DAG module imports without the real
package. External effects (FEMA/DB date lookups, shapefile download, the
ingestion subprocess) are monkeypatched; no network or Airflow runtime is used.
"""

import pytest

import nfhl_refresh_dag as dag


class FakeCompleted:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def install(monkeypatch, *, fema, db, run_result=None, download_calls=None,
            run_calls=None):
    """Wire the common monkeypatches; return nothing."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://test")
    monkeypatch.setattr(dag, "get_latest_eff_date", lambda s: fema)
    monkeypatch.setattr(dag, "get_current_eff_date", lambda s, url: db)

    def fake_download(state_fips):
        if download_calls is not None:
            download_calls.append(state_fips)
        return dag.DATA_DIR / f"S_FLD_HAZ_AR_{state_fips}.shp"

    monkeypatch.setattr(dag, "download_state_shapefile", fake_download)

    def fake_run(*args, **kwargs):
        if run_calls is not None:
            run_calls.append((args, kwargs))
        return run_result if run_result is not None else FakeCompleted(0)

    monkeypatch.setattr(dag.subprocess, "run", fake_run)


def test_validates_state_fips(monkeypatch):
    with pytest.raises(ValueError):
        dag.check_and_refresh("bad")


def test_raises_when_db_url_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(ValueError, match="SUPABASE_DB_URL"):
        dag.check_and_refresh("12")


def test_skips_when_fema_date_unavailable(monkeypatch):
    downloads = []
    install(monkeypatch, fema=None, db="2010-03-01", download_calls=downloads)
    dag.check_and_refresh("12")
    assert downloads == []  # no ingestion attempted


def test_skips_when_data_is_current(monkeypatch):
    downloads = []
    install(monkeypatch, fema="2010-01-01", db="2010-03-01", download_calls=downloads)
    dag.check_and_refresh("12")
    assert downloads == []  # FEMA not newer -> no ingestion


def test_ingests_when_fema_is_newer(monkeypatch, tmp_path):
    script = tmp_path / "ingest_nfhl.sh"
    script.write_text("#!/usr/bin/env bash\n")
    monkeypatch.setenv("FLOODLENS_INGEST_SCRIPT_PATH", str(script))

    downloads, runs = [], []
    install(monkeypatch, fema="2020-01-01", db="2010-03-01",
            download_calls=downloads, run_calls=runs)

    dag.check_and_refresh("12")

    assert downloads == ["12"]
    assert len(runs) == 1
    cmd = runs[0][0][0]
    assert cmd[0] == str(script)
    assert cmd[2] == "12"
    env = runs[0][1]["env"]
    assert env["NFHL_EFF_DATE"] == "2020-01-01"
    assert env["SUPABASE_DB_URL"] == "postgres://test"


def test_ingests_when_db_has_no_rows(monkeypatch, tmp_path):
    script = tmp_path / "ingest_nfhl.sh"
    script.write_text("#!/usr/bin/env bash\n")
    monkeypatch.setenv("FLOODLENS_INGEST_SCRIPT_PATH", str(script))

    downloads, runs = [], []
    install(monkeypatch, fema="2020-01-01", db=None,
            download_calls=downloads, run_calls=runs)

    dag.check_and_refresh("12")
    assert downloads == ["12"]  # db_date None must not block ingestion


def test_raises_when_ingest_script_missing(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "FLOODLENS_INGEST_SCRIPT_PATH", str(tmp_path / "does-not-exist.sh")
    )
    install(monkeypatch, fema="2020-01-01", db="2010-03-01")
    with pytest.raises(FileNotFoundError):
        dag.check_and_refresh("12")


def test_raises_when_ingestion_subprocess_fails(monkeypatch, tmp_path):
    script = tmp_path / "ingest_nfhl.sh"
    script.write_text("#!/usr/bin/env bash\n")
    monkeypatch.setenv("FLOODLENS_INGEST_SCRIPT_PATH", str(script))

    install(monkeypatch, fema="2020-01-01", db="2010-03-01",
            run_result=FakeCompleted(returncode=1, stderr="boom"))
    with pytest.raises(RuntimeError):
        dag.check_and_refresh("12")
