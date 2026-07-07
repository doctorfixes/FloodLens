#!/usr/bin/env python3
"""Integration proof: ingest a non-Denver FEMA feature and query flood risk.

Exercises the real loader transform (`feature_to_insert`) against a live
PostgreSQL + PostGIS database loaded with the flood_zones schema and
`fn_get_flood_risk`, using a Florida fixture. Proves that ingestion and the
spatial risk lookup work outside Denver — the pipeline is not region-specific.

Runs locally and in CI (the pgtap-test job already provisions the database).
Shells out to psql so no Python DB driver is required.

Usage:
  python tests/integration/verify_multistate_ingest.py [--database floodlens_test]

Exit code 0 on success, 1 on any assertion failure.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from load_fema_data import feature_to_insert  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "fema-feature-fl.json"

# A point inside the Florida fixture polygon (Miami-Dade), well outside Denver.
FL_LAT, FL_LNG = 25.76, -80.19
EXPECTED_ZONE = "AE"
EXPECTED_RISK = "HIGH"
EXPECTED_STATE_FIPS = "12"


def psql(sql: str, database: str) -> str:
    """Run a single SQL statement via psql, returning stripped stdout."""
    result = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", database, "-tAc", sql],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql failed: {result.stderr.strip()}\nSQL: {sql}")
    return result.stdout.strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="floodlens_test")
    args = parser.parse_args(argv)
    db = args.database

    feature = json.loads(FIXTURE.read_text())
    insert_sql = feature_to_insert(feature)
    if not insert_sql:
        print("FAIL: feature_to_insert produced no SQL for the fixture", file=sys.stderr)
        return 1

    # Clean slate, then ingest via the real transform.
    psql("TRUNCATE public.flood_zones;", db)
    psql(insert_sql, db)

    # Idempotency: re-running the same INSERT must not create a duplicate.
    psql(insert_sql, db)
    row_count = psql("SELECT count(*) FROM public.flood_zones;", db)
    if row_count != "1":
        print(f"FAIL: expected 1 row after duplicate insert, got {row_count}", file=sys.stderr)
        return 1

    # State FIPS must be derived from DFIRM_ID (12086C -> '12').
    state_fips = psql("SELECT state_fips FROM public.flood_zones LIMIT 1;", db)
    if state_fips != EXPECTED_STATE_FIPS:
        print(f"FAIL: expected state_fips {EXPECTED_STATE_FIPS}, got {state_fips}", file=sys.stderr)
        return 1

    # The spatial risk lookup must return the correct zone at the FL point.
    result = psql(
        f"SELECT zone_code || '|' || risk_level "
        f"FROM public.fn_get_flood_risk({FL_LAT}, {FL_LNG});",
        db,
    )
    if result != f"{EXPECTED_ZONE}|{EXPECTED_RISK}":
        print(
            f"FAIL: expected {EXPECTED_ZONE}|{EXPECTED_RISK} at the FL point, got {result!r}",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: ingested Florida feature (state_fips={state_fips}); "
        f"fn_get_flood_risk({FL_LAT}, {FL_LNG}) = {result}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
