"""Tests for dags/utils/db_client.py::get_current_eff_date.

psycopg2 is stubbed in conftest.py; each test installs a fake ``connect``
that emulates the connection/cursor context-manager protocol.
"""

from datetime import date

import pytest

from utils import db_client


class FakeCursor:
    def __init__(self, row):
        self._row = row
        self.executed = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed = (sql, params)

    def fetchone(self):
        return self._row


class FakeConn:
    def __init__(self, row):
        self.cursor_obj = FakeCursor(row)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self.cursor_obj


def make_connect(row):
    def _connect(_db_url):
        return FakeConn(row)

    return _connect


def test_returns_iso_date_when_row_present(monkeypatch):
    monkeypatch.setattr(
        db_client.psycopg2, "connect", make_connect((date(2010, 3, 1),))
    )
    assert db_client.get_current_eff_date("12", "postgres://x") == "2010-03-01"


def test_returns_none_when_no_rows(monkeypatch):
    monkeypatch.setattr(db_client.psycopg2, "connect", make_connect(None))
    assert db_client.get_current_eff_date("12", "postgres://x") is None


def test_returns_none_when_max_eff_date_is_null(monkeypatch):
    monkeypatch.setattr(db_client.psycopg2, "connect", make_connect((None,)))
    assert db_client.get_current_eff_date("12", "postgres://x") is None


def test_returns_none_on_db_exception(monkeypatch):
    def boom(_db_url):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(db_client.psycopg2, "connect", boom)
    assert db_client.get_current_eff_date("12", "postgres://x") is None


def test_passes_state_fips_as_bind_parameter(monkeypatch):
    conn = FakeConn((date(2010, 3, 1),))
    monkeypatch.setattr(db_client.psycopg2, "connect", lambda _db_url: conn)

    db_client.get_current_eff_date("12", "postgres://x")

    sql, params = conn.cursor_obj.executed
    # Guard against string interpolation of the FIPS value into SQL.
    assert params == ("12",)
    assert "%s" in sql


def test_rejects_invalid_state_fips(monkeypatch):
    with pytest.raises(ValueError):
        db_client.get_current_eff_date("bad", "postgres://x")
