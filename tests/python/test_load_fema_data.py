"""Tests for scripts/load_fema_data.py pure transform helpers."""

import load_fema_data as loader


# ── is_valid_bfe ───────────────────────────────────────────────────────────

def test_is_valid_bfe_rejects_none_and_sentinels():
    assert loader.is_valid_bfe(None) is False
    assert loader.is_valid_bfe(-9999) is False
    # Boundary: the `> -9998` check also excludes exactly -9998.
    assert loader.is_valid_bfe(-9998) is False
    assert loader.is_valid_bfe("not-a-number") is False


def test_is_valid_bfe_accepts_real_values():
    assert loader.is_valid_bfe(-9997) is True
    assert loader.is_valid_bfe(0) is True
    assert loader.is_valid_bfe(452.0) is True
    assert loader.is_valid_bfe("452") is True


# ── escape ─────────────────────────────────────────────────────────────────

def test_escape_null_and_single_quotes():
    assert loader.escape(None) == "NULL"
    assert loader.escape("abc") == "'abc'"
    assert loader.escape("O'Brien") == "'O''Brien'"


def test_escape_doubles_backslashes_current_behavior():
    # Documents CURRENT behaviour. With PostgreSQL's default
    # standard_conforming_strings=on, backslashes are literal, so doubling
    # them corrupts the stored value. Flagged in the coverage analysis as a
    # latent loader bug; pinned here so an intentional fix updates this test.
    assert loader.escape("a\\b") == "'a\\\\b'"


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
