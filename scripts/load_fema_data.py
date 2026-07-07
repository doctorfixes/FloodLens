#!/usr/bin/env python3
"""
Paginated FEMA NFHL data loader for ZoneCheck.

Downloads flood zone features from FEMA's ArcGIS REST API (Layer 28, NFHL) for
a bounding box, converts them to SQL INSERT statements, and executes them via
the Supabase Management API.

The bounding box, region label, and target Supabase project are all
configurable, so the loader can ingest any state/metro — not just Denver.

Usage:
  # Denver metro (default), project from $SUPABASE_PROJECT_REF or built-in
  python scripts/load_fema_data.py

  # Miami-Dade, FL into a specific project. Use --bbox=... (equals form) so a
  # leading-negative longitude is not parsed as an option flag.
  python scripts/load_fema_data.py \
    --name "Miami-Dade FL" \
    --bbox=-80.9,25.1,-80.1,25.9 \
    --project-ref abcdefghijklmnop

Environment:
  SUPABASE_SERVICE_KEY / SUPABASE_ACCESS_TOKEN  Management API bearer token.
  SUPABASE_PROJECT_REF                          Default project ref (overridable via --project-ref).
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

# ── Configuration ──────────────────────────────────────────────────────────

FEMA_BASE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"

# Default region: Denver metro bounding box (min_x, min_y, max_x, max_y) in EPSG:4326.
DEFAULT_BBOX = (-105.1, 39.6, -104.9, 39.8)

DEFAULT_PROJECT_REF = "htnufvbzsfdfadnnfnje"
SUPABASE_PROJECT_REF = os.environ.get("SUPABASE_PROJECT_REF", DEFAULT_PROJECT_REF)

# Get service key from env or try SUPABASE_ACCESS_TOKEN
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ACCESS_TOKEN", "")

PAGE_SIZE = 500      # Max results per API call
BATCH_SIZE = 50      # Max INSERTs per SQL query (payload size management)

# ── Helper functions ──────────────────────────────────────────────────────

def geometry_param(bbox) -> str:
    """Build the ArcGIS envelope geometry query fragment for a bounding box."""
    min_x, min_y, max_x, max_y = bbox
    return (
        f"&geometry={min_x}%2C{min_y}%2C{max_x}%2C{max_y}"
        f"&geometryType=esriGeometryEnvelope&inSR=4326"
    )


def count_features(bbox, fema_base: str = FEMA_BASE) -> int:
    """Return the total NFHL feature count within the bounding box."""
    params = (
        f"where=1%3D1"
        f"{geometry_param(bbox)}"
        f"&returnGeometry=false&returnCountOnly=true&f=json"
    )
    url = f"{fema_base}?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode()).get("count", 0)


def fetch_page(offset: int, count: int, bbox, fema_base: str = FEMA_BASE) -> dict:
    """Fetch one page of FEMA features for the bounding box."""
    params = (
        f"where=1%3D1"
        f"{geometry_param(bbox)}"
        f"&outFields=*"
        f"&returnGeometry=true&f=geojson"
        f"&outSR=4326"
        f"&resultOffset={offset}"
        f"&resultRecordCount={count}"
    )
    url = f"{fema_base}?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} at offset {offset}: {e.read().decode()[:200]}", file=sys.stderr)
        return {"features": []}
    except Exception as e:
        print(f"Error at offset {offset}: {e}", file=sys.stderr)
        return {"features": []}
    return data


def is_valid_bfe(val) -> bool:
    """Check if a BFE/DEPTH/VELOCITY value is valid (not FEMA's -9999 sentinel)."""
    if val is None:
        return False
    try:
        v = float(val)
        return v > -9999  # -9999 = no data sentinel
    except (ValueError, TypeError):
        return False


def feature_to_insert(f: dict) -> str:
    """Convert a GeoJSON feature to a SQL INSERT statement."""
    props = f.get("properties", {})
    geom = f.get("geometry")

    if not geom or not props:
        return ""

    dfirm_id = props.get("DFIRM_ID", "")
    if not dfirm_id:
        return ""

    # Extract state/county FIPS from DFIRM_ID (first 2 = state, first 5 = county)
    state_fips = dfirm_id[:2] if len(dfirm_id) >= 2 else None
    county_fips = dfirm_id[:5] if len(dfirm_id) >= 5 else None

    # Source feature ID = FLD_AR_ID
    source_feature_id = props.get("FLD_AR_ID", "")

    # Zone code
    m_zone_code = props.get("FLD_ZONE", "")

    # Zone subtype (e.g. "FLOODWAY")
    zone_subtype = props.get("ZONE_SUBTY") or None

    # Numerical fields with -9999 sentinel → NULL
    static_bfe = str(round(float(props["STATIC_BFE"]), 2)) if is_valid_bfe(props.get("STATIC_BFE")) else "NULL"
    depth       = str(round(float(props["DEPTH"]), 2))     if is_valid_bfe(props.get("DEPTH"))       else "NULL"
    velocity    = str(round(float(props["VELOCITY"]), 2))  if is_valid_bfe(props.get("VELOCITY"))    else "NULL"

    # Source citation
    source_citation = props.get("SOURCE_CIT") or None

    # panel_number: use FLD_AR_ID if present OR build from DFIRM_ID + sequence
    panel_number = props.get("FLD_AR_ID") or None

    # Geometry: Polygon → MultiPolygon wrapper for schema compliance
    geom_json = json.dumps(geom)

    # Build column list and values
    cols = ", ".join([
        "geometry", "dfirm_id", "panel_number", "m_zone_code",
        "static_bfe", "depth", "velocity", "source_citation",
        "state_fips", "county_fips", "source_feature_id", "zone_subtype"
    ])

    vals = ", ".join([
        f"ST_Multi(ST_GeomFromGeoJSON('{geom_json}'))",
        escape(dfirm_id),
        escape(panel_number),
        escape(m_zone_code),
        static_bfe,
        depth,
        velocity,
        escape(source_citation),
        escape(state_fips),
        escape(county_fips),
        escape(source_feature_id),
        escape(zone_subtype)
    ])

    # Dedup target is the partial UNIQUE INDEX idx_flood_zones_unique_source_feature
    # (state_fips, source_feature_id, eff_date) WHERE source_feature_id IS NOT NULL.
    # It is an index, not a named constraint, so ON CONFLICT must infer it by
    # column list + predicate — `ON CONFLICT ON CONSTRAINT <index>` is invalid.
    return (
        f"INSERT INTO public.flood_zones ({cols}) VALUES ({vals}) "
        f"ON CONFLICT (state_fips, source_feature_id, eff_date) "
        f"WHERE source_feature_id IS NOT NULL DO NOTHING;"
    )


def escape(val) -> str:
    """SQL-safe string literal or NULL.

    PostgreSQL runs with standard_conforming_strings=on by default, so
    backslashes inside a single-quoted literal are ordinary characters.
    Only single quotes need doubling; doubling backslashes would corrupt
    the stored value.
    """
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def run_sql(sql: str, project_ref: str, service_key: str = "") -> dict:
    """Execute SQL on Supabase via the Management API."""
    service_key = service_key or SUPABASE_SERVICE_KEY
    url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
    payload = json.dumps({"query": sql}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {service_key}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return {"ok": True, "body": resp.read().decode()[:500]}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"ok": False, "code": e.code, "body": body[:1000]}


# ── CLI ────────────────────────────────────────────────────────────────────

def _bbox(s: str):
    """argparse type: parse 'min_x,min_y,max_x,max_y' into a tuple of floats."""
    parts = s.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be 'min_x,min_y,max_x,max_y'")
    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        raise argparse.ArgumentTypeError("bbox values must be numbers")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Load FEMA NFHL flood zones for a bounding box into Supabase."
    )
    p.add_argument(
        "--bbox", type=_bbox, default=DEFAULT_BBOX,
        help="Bounding box 'min_x,min_y,max_x,max_y' in EPSG:4326 (default: Denver metro).",
    )
    p.add_argument(
        "--project-ref", default=SUPABASE_PROJECT_REF,
        help="Supabase project ref to load into (default: $SUPABASE_PROJECT_REF or built-in).",
    )
    p.add_argument(
        "--name", default="region",
        help="Human-readable region label used in log output.",
    )
    p.add_argument(
        "--page-size", type=int, default=PAGE_SIZE,
        help=f"FEMA API page size (default: {PAGE_SIZE}).",
    )
    return p.parse_args(argv)


# ── Main ──────────────────────────────────────────────────────────────────

def main(argv=None):
    args = parse_args(argv)

    if not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_SERVICE_KEY or SUPABASE_ACCESS_TOKEN not set.", file=sys.stderr)
        sys.exit(1)

    bbox = args.bbox
    project_ref = args.project_ref
    name = args.name
    page_size = args.page_size

    # Step 1: Get total count
    print(f"Getting feature count for {name}...")
    total = count_features(bbox)
    print(f"Total features in {name} bounding box: {total}")

    if total == 0:
        print("No features found. Exiting.")
        return

    # Step 2: Paginate and collect
    all_sql = []
    seen_zones = set()

    for offset in range(0, total, page_size):
        actual_page = min(page_size, total - offset)
        print(f"  Fetching offset {offset} ({actual_page} features)...")
        data = fetch_page(offset, actual_page, bbox)
        features = data.get("features", [])
        print(f"    Got {len(features)} features")
        for f in features:
            sql = feature_to_insert(f)
            if sql:
                all_sql.append(sql)
                z = f.get("properties", {}).get("FLD_ZONE")
                if z:
                    seen_zones.add(z)
        time.sleep(0.5)  # Be nice to FEMA API

    print(f"\nGenerated {len(all_sql)} INSERT statements")
    print(f"Zone codes found: {sorted(seen_zones)}")

    # Step 3: Batch execute
    print(f"\nExecuting in batches of {BATCH_SIZE}...")
    success = 0
    failed = 0

    for i in range(0, len(all_sql), BATCH_SIZE):
        batch = all_sql[i:i + BATCH_SIZE]
        batch_sql = "\n".join(batch)
        pct = int(i / len(all_sql) * 100)
        print(f"  [{pct}%] Batch {i//BATCH_SIZE + 1}/{-(-len(all_sql)//BATCH_SIZE)} ({len(batch)} INSERTs)...", end=" ")

        result = run_sql(batch_sql, project_ref)
        if result["ok"]:
            success += len(batch)
            print("OK")
        else:
            failed += len(batch)
            print(f"FAILED (HTTP {result['code']})")
            print(f"  Error: {result['body'][:300]}")

        time.sleep(0.1)

    # Summary
    print(f"\n{'='*50}")
    print(f"DONE: {success} inserted, {failed} failed")
    print(f"Zones ingested: {sorted(seen_zones)}")

    # Step 4: Verify
    print("\nVerifying with a test query...")
    test_sql = "SELECT m_zone_code, COUNT(*) as cnt FROM public.flood_zones GROUP BY m_zone_code ORDER BY m_zone_code;"
    result = run_sql(test_sql, project_ref)
    if result["ok"]:
        print(f"Result: {result['body']}")
    else:
        print(f"Verify error: {result['body']}")

    # Test the flood risk function at the bounding-box centre.
    min_x, min_y, max_x, max_y = bbox
    center_lat = (min_y + max_y) / 2
    center_lng = (min_x + max_x) / 2
    print(f"\nTesting fn_get_flood_risk at {name} centre ({center_lat:.4f}, {center_lng:.4f})...")
    test_risk = f"SELECT * FROM public.fn_get_flood_risk({center_lat}, {center_lng});"
    result = run_sql(test_risk, project_ref)
    if result["ok"]:
        print(f"Flood risk: {result['body']}")
    else:
        print(f"Risk query error: {result['body']}")


if __name__ == "__main__":
    main()
