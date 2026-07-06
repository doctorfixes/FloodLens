"""Tests for dags/utils/fema_client.py::get_latest_eff_date."""

import pytest

from utils import fema_client


class FakeResponse:
    def __init__(self, payload, raise_exc=None):
        self._payload = payload
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._payload


def test_returns_iso_date_from_epoch_milliseconds(monkeypatch):
    # 1_267_401_600_000 ms == 2010-03-01T00:00:00Z
    payload = {"features": [{"attributes": {"EFF_DATE": 1_267_401_600_000}}]}
    monkeypatch.setattr(
        fema_client.requests, "get", lambda *a, **k: FakeResponse(payload)
    )
    assert fema_client.get_latest_eff_date("12") == "2010-03-01"


def test_returns_none_when_no_features(monkeypatch):
    monkeypatch.setattr(
        fema_client.requests,
        "get",
        lambda *a, **k: FakeResponse({"features": []}),
    )
    assert fema_client.get_latest_eff_date("12") is None


def test_returns_none_on_request_exception(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(fema_client.requests, "get", boom)
    assert fema_client.get_latest_eff_date("12") is None


def test_validates_state_fips_before_hitting_the_network(monkeypatch):
    calls = {"n": 0}

    def spy(*a, **k):
        calls["n"] += 1
        return FakeResponse({"features": []})

    monkeypatch.setattr(fema_client.requests, "get", spy)
    with pytest.raises(ValueError):
        fema_client.get_latest_eff_date("999")
    assert calls["n"] == 0
