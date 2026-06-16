#!/usr/bin/env python3
"""
Generate a Supabase migration SQL file containing all Denver FEMA NFHL flood zone data.

Downloads 2,348 features from FEMA's ArcGIS REST API (Layer 28),
converts to multi-row INSERT statements, and writes a migration file.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

# ── Configuration ──────────────────────────────────────────────────────────

FEMA_BASE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"

MIN_X, MIN_Y = -105.1, 39.6  # Denver bounding box
MAX_X, MAX_Y = -104.9, 39.8

PAGE_SIZE = 500
ROWS_PER_INSERT = 100   # Number of rows per multi-row VALUES insert

# ── Helpers ────────────────────────────────────────────────────────────────


def fetch_page(offset: int) -> dict:
    """Fetch one page of FEMA features."""
    params = (
        f"where=1%3D1"
        f"&geometry={MIN_X}%2C{MIN_Y}%2C{MAX_X}%2C{MAX_Y}"
        f"&geometryType=esriGeometryEnvelope&inSR=4326"
        f"&outFields=*&returnGeometry=true&f=geojson"
        f"&outSR=4326&resultOffset={offset}&resultRecordCount={PAGE_SIZE}"
    )
    url = f"{FEMA_BASE}?{params}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode())


def sq(v):
    """SQL-escape a string value, returning NULL for None."""
    if v is None or v == "":
        return "NULL"
    escaped = str(v).replace("'", "''").replace("\\", "\\\\")
    return f"'{escaped}'"


def col_val(v, is_numeric=False):
    """Return SQL value, converting FEMA's -9999 sentinel to NULL."""
    if v is None:
        return "NULL"
    try:
        n = float(v)
        if n <= -9998:
            return "NULL"
        if is_numeric:
            return str(n)
    except (ValueError, TypeError):
        pass
    return sq(str(v))


def build_insert(features_batch: list) -> str:
    """Build a multi-row INSERT statement for a batch of features."""
    values_rows = []
    for f in features_batch:
        props = f.get("properties", {})
        geom = f.get("geometry")
        if not geom or not props.get("DFIRM_ID"):
            continue

        d = props["DFIRM_ID"]
        fa = props.get("FLD_AR_ID") or ""
        z = props["FLD_ZONE"]
        sf = props.get("SFHA_TF") or ""

        # Zone subtype
        zt = props.get("ZONE_SUBTY") or ""

        # BFE / Depth / Velocity (-9999 → NULL)
        bfe_val = col_val(props.get("STATIC_BFE"), is_numeric=True)
        depth_val = col_val(props.get("DEPTH"), is_numeric=True)
        vel_val = col_val(props.get("VELOCITY"), is_numeric=True)

        sc = props.get("SOURCE_CIT") or ""

        state_fips = d[:2] if len(d) >= 2 else ""
        county_fips = d[:5] if len(d) >= 5 else ""

        # Geometry: ensure MultiPolygon
        geom_json = json.dumps(geom)

        # Build one row of values
        row = (
            f"  (ST_Multi(ST_GeomFromGeoJSON('{geom_json.replace(chr(39), chr(39)+chr(39))}')), "
            f"{sq(d)}, {sq(fa)}, {sq(z)}, "
            f"{bfe_val}, {depth_val}, {vel_val}, "
            f"{sq(sc)}, {sq(state_fips)}, {sq(county_fips)}, "
            f"{sq(fa)}, {sq(zt)})"
        )
        values_rows.append(row)

    if not values_rows:
        return ""

    cols = (
        "geometry, dfirm_id, panel_number, m_zone_code, "
        "static_bfe, depth, velocity, source_citation, "
        "state_fips, county_fips, source_feature_id, zone_subtype"
    )

    return (
        f"INSERT INTO public.flood_zones ({cols}) VALUES\n"
        + ",\n".join(values_rows)
        + "\nON CONFLICT ON CONSTRAINT idx_flood_zones_unique_source_feature DO NOTHING;\n"
    )


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else (
        os.path.expanduser("~/ZoneCheck/supabase/migrations/00004_load_denver_flood_zones.sql")
    )

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
    print(f"Total features: {total}")

    if total == 0:
        print("No features found.")
        return

    # Step 2: Paginate and collect all features
    all_features = []
    seen_zones = set()

    for offset in range(0, total, PAGE_SIZE):
        print(f"  Fetching offset {offset}...", end=" ", flush=True)
        data = fetch_page(offset)
        features = data.get("features", [])
        print(f"{len(features)} features")
        all_features.extend(features)
        for f in features:
            z = f.get("properties", {}).get("FLD_ZONE")
            if z:
                seen_zones.add(z)
        time.sleep(0.3)

    print(f"\nTotal collected: {len(all_features)}")
    print(f"Zone codes: {sorted(seen_zones)}")

    # Step 3: Write migration SQL file
    with open(output_path, "w") as f:
        f.write("-- Migration: Load Denver flood zone data from FEMA NFHL\n")
        f.write("-- Generated: June 2026\n")
        f.write("-- Source: FEMA NFHL MapServer Layer 28\n")
        f.write(f"-- Bounding box: {MIN_X},{MIN_Y} to {MAX_X},{MAX_Y}\n")
        f.write(f"-- Features: {total}\n")
        f.write(f"-- Zone codes: {', '.join(sorted(seen_zones))}\n\n")

        # Batch into multi-row INSERTs
        inserted = 0
        for i in range(0, len(all_features), ROWS_PER_INSERT):
            batch = all_features[i : i + ROWS_PER_INSERT]
            sql = build_insert(batch)
            if sql:
                f.write(sql + "\n")
                inserted += len(batch)

        f.write(f"\n-- Inserted {inserted} records\n")

    file_size = os.path.getsize(output_path)
    print(f"\nWritten: {output_path}")
    print(f"Size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")
    print(f"Features: {inserted}")


if __name__ == "__main__":
    main()