#!/usr/bin/env python3
"""
Paginated FEMA NFHL data loader for ZoneCheck.

Downloads flood zone features from FEMA's ArcGIS REST API (Layer 28, NFHL),
converts to SQL INSERT statements, and executes via Supabase Management API.

Usage:
  python scripts/load_fema_data.py
  SUPABASE_SERVICE_KEY="..." python scripts/load_fema_data.py
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

# ── Configuration ──────────────────────────────────────────────────────────

FEMA_BASE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"

# Denver metro bounding box (lat/lon, EPSG:4326 envelope)
MIN_X, MIN_Y = -105.1, 39.6
MAX_X, MAX_Y = -104.9, 39.8

SUPABASE_PROJECT_REF = "htnufvbzsfdfadnnfnje"

# Get service key from env or try SUPABASE_ACCESS_TOKEN
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ACCESS_TOKEN", "")

PAGE_SIZE = 500      # Max results per API call
BATCH_SIZE = 50      # Max INSERTs per SQL query (payload size management)

# ── Helper functions ──────────────────────────────────────────────────────

def fetch_page(offset: int, count: int = PAGE_SIZE) -> dict:
    """Fetch one page of FEMA features."""
    params = (
        f"where=1%3D1"
        f"&geometry={MIN_X}%2C{MIN_Y}%2C{MAX_X}%2C{MAX_Y}"
        f"&geometryType=esriGeometryEnvelope&inSR=4326"
        f"&outFields=*"
        f"&returnGeometry=true&f=geojson"
        f"&outSR=4326"
        f"&resultOffset={offset}"
        f"&resultRecordCount={count}"
    )
    url = f"{FEMA_BASE}?{params}"
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
        return v > -9998  # -9999 = no data
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

    return f"INSERT INTO public.flood_zones ({cols}) VALUES ({vals}) ON CONFLICT ON CONSTRAINT idx_flood_zones_unique_source_feature DO NOTHING;"


def escape(val) -> str:
    """SQL-safe string literal or NULL."""
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''").replace("\\", "\\\\")
    return f"'{escaped}'"


def run_sql(sql: str) -> dict:
    """Execute SQL on Supabase via Management API."""
    url = f"https://api.supabase.com/v1/projects/{SUPABASE_PROJECT_REF}/database/query"
    payload = json.dumps({"query": sql}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {SUPABASE_SERVICE_KEY}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return {"ok": True, "body": resp.read().decode()[:500]}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"ok": False, "code": e.code, "body": body[:1000]}


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    if not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_SERVICE_KEY or SUPABASE_ACCESS_TOKEN not set.", file=sys.stderr)
        sys.exit(1)

    # Step 1: Get total count
    print("Getting feature count...")
    params = (
        f"where=1%3D1"
        f"&geometry={MIN_X}%2C{MIN_Y}%2C{MAX_X}%2C{MAX_Y}"
        f"&geometryType=esriGeometryEnvelope&inSR=4326"
        f"&returnGeometry=false&returnCountOnly=true&f=json"
    )
    url = f"{FEMA_BASE}?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        count_data = json.loads(resp.read().decode())
    total = count_data.get("count", 0)
    print(f"Total features in Denver bounding box: {total}")

    if total == 0:
        print("No features found. Exiting.")
        return

    # Step 2: Paginate and collect
    all_sql = []
    seen_zones = set()

    for offset in range(0, total, PAGE_SIZE):
        actual_page = min(PAGE_SIZE, total - offset)
        print(f"  Fetching offset {offset} ({actual_page} features)...")
        data = fetch_page(offset, actual_page)
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

        result = run_sql(batch_sql)
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
    result = run_sql(test_sql)
    if result["ok"]:
        print(f"Result: {result['body']}")
    else:
        print(f"Verify error: {result['body']}")

    # Test flood risk function for a Denver location
    print("\nTesting fn_get_flood_risk for a Denver address...")
    test_risk = "SELECT * FROM public.fn_get_flood_risk(39.74, -104.99);"
    result = run_sql(test_risk)
    if result["ok"]:
        print(f"Flood risk: {result['body']}")
    else:
        print(f"Risk query error: {result['body']}")


if __name__ == "__main__":
    main()