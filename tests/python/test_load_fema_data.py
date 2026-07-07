"""Tests for scripts/load_fema_data.py pure transform helpers."""

import pytest

import load_fema_data as loader


# ── is_valid_bfe ───────────────────────────────────────────────────────────

def test_is_valid_bfe_rejects_none_and_sentinel():
    assert loader.is_valid_bfe(None) is False
    assert loader.is_valid_bfe(-9999) is False
    assert loader.is_valid_bfe("not-a-number") is False


def test_is_valid_bfe_accepts_real_values():
    # -9998 is a real value: only -9999 is the "no data" sentinel.
    assert loader.is_valid_bfe(-9998) is True
    assert loader.is_valid_bfe(-9997) is True
    assert loader.is_valid_bfe(0) is True
    assert loader.is_valid_bfe(452.0) is True
    assert loader.is_valid_bfe("452") is True


# ── escape ─────────────────────────────────────────────────────────────────

def test_escape_null_and_single_quotes():
    assert loader.escape(None) == "NULL"
    assert loader.escape("abc") == "'abc'"
    assert loader.escape("O'Brien") == "'O''Brien'"


def test_escape_preserves_literal_backslashes():
    # With PostgreSQL's default standard_conforming_strings=on, backslashes
    # are literal inside a single-quoted string, so they must pass through
    # unchanged. "a\\b" is the 3-char string a-backslash-b.
    assert loader.escape("a\\b") == "'a\\b'"


# ── feature_to_insert ──────────────────────────────────────────────────────

def test_feature_to_insert_skips_incomplete_features():
    assert loader.feature_to_insert({}) == ""
    # Missing geometry.
    assert loader.feature_to_insert({"properties": {"DFIRM_ID": "08031C"}}) == ""
    # Present geometry + props but no DFIRM_ID.
    assert (
        loader.feature_to_insert(
            {"geometry": {"type": "Polygon"}, "properties": {"FLD_ZONE": "AE"}}
        )
        == ""
    )


def test_feature_to_insert_builds_statement_with_sentinel_nulls():
    feature = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
        },
        "properties": {
            "DFIRM_ID": "08031C",
            "FLD_AR_ID": "08031C_123",
            "FLD_ZONE": "AE",
            "ZONE_SUBTY": "FLOODWAY",
            "STATIC_BFE": 5280.5,
            "DEPTH": -9999,
            "VELOCITY": -9999,
            "SOURCE_CIT": "STUDY-1",
        },
    }

    sql = loader.feature_to_insert(feature)

    assert sql.startswith("INSERT INTO public.flood_zones")
    assert "ST_Multi(ST_GeomFromGeoJSON(" in sql
    assert "'08031C'" in sql          # dfirm_id
    assert "'AE'" in sql              # zone code
    assert "'08'" in sql             # state_fips = DFIRM_ID[:2]
    assert "'08031'" in sql          # county_fips = DFIRM_ID[:5]
    assert "5280.5" in sql           # valid static_bfe kept
    assert "ON CONFLICT" in sql


def test_feature_to_insert_uses_partial_index_inference_not_constraint():
    # idx_flood_zones_unique_source_feature is a partial UNIQUE INDEX, not a
    # named constraint, so the upsert must infer it by columns + predicate.
    # `ON CONFLICT ON CONSTRAINT <index>` is invalid SQL and must not appear.
    feature = {
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        "properties": {"DFIRM_ID": "12086C", "FLD_AR_ID": "12086C_1", "FLD_ZONE": "AE"},
    }
    sql = loader.feature_to_insert(feature)
    assert "ON CONSTRAINT" not in sql
    assert (
        "ON CONFLICT (state_fips, source_feature_id, eff_date) "
        "WHERE source_feature_id IS NOT NULL DO NOTHING" in sql
    )


# ── bounding-box parameterization (no longer hard-coded to Denver) ──────────

def test_geometry_param_reflects_custom_bbox():
    frag = loader.geometry_param((-80.9, 25.1, -80.1, 25.9))
    assert "geometry=-80.9%2C25.1%2C-80.1%2C25.9" in frag
    assert "esriGeometryEnvelope" in frag


def test_default_bbox_is_denver():
    assert loader.DEFAULT_BBOX == (-105.1, 39.6, -104.9, 39.8)


def test_parse_args_defaults():
    args = loader.parse_args([])
    assert args.bbox == loader.DEFAULT_BBOX
    assert args.project_ref == loader.DEFAULT_PROJECT_REF


def test_parse_args_accepts_custom_bbox_and_project():
    # Values starting with '-' must use the --bbox=... form so argparse does
    # not mistake the negative longitude for an option flag.
    args = loader.parse_args(
        ["--bbox=-80.9,25.1,-80.1,25.9", "--project-ref", "abcdef", "--name", "Miami"]
    )
    assert args.bbox == (-80.9, 25.1, -80.1, 25.9)
    assert args.project_ref == "abcdef"
    assert args.name == "Miami"


def test_parse_args_rejects_malformed_bbox():
    with pytest.raises(SystemExit):
        loader.parse_args(["--bbox", "1,2,3"])
    with pytest.raises(SystemExit):
        loader.parse_args(["--bbox", "a,b,c,d"])
