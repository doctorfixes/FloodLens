#!/usr/bin/env bash
# ingest_nfhl.sh — ogr2ogr ingestion script for FEMA NFHL shapefiles
# Loads flood zone polygons from a state NFHL shapefile into PostGIS.
#
# Usage: ./ingest_nfhl.sh <STATE_FIPS>
# Example: ./ingest_nfhl.sh 06   # California
#
# Required environment variables:
#   DATABASE_URL  PostgreSQL connection string (postgres://user:pass@host:port/db)
#
# Optional environment variables:
#   DATA_DIR      Base directory for shapefiles (default: data)
#   NFHL_LAYER    OGR layer name to import (default: S_FLD_HAZ_AR)

set -euo pipefail

STATE_FIPS="${1:?Usage: $0 <STATE_FIPS>}"
DATABASE_URL="${DATABASE_URL:?DATABASE_URL environment variable is required}"
DATA_DIR="${DATA_DIR:-data}"
NFHL_LAYER="${NFHL_LAYER:-S_FLD_HAZ_AR}"

# Zero-pad to 2 digits
STATE_FIPS=$(printf "%02d" "${STATE_FIPS#0}")

SHP_DIR="${DATA_DIR}/${STATE_FIPS}"

if [ ! -d "${SHP_DIR}" ]; then
  echo "[ingest_nfhl] ERROR: Shapefile directory '${SHP_DIR}' not found." >&2
  echo "[ingest_nfhl] Run download_nfhl.sh ${STATE_FIPS} first." >&2
  exit 1
fi

# Find the flood hazard area shapefile
SHP_FILE=$(find "${SHP_DIR}" -iname "${NFHL_LAYER}.shp" | head -n 1)

if [ -z "${SHP_FILE}" ]; then
  echo "[ingest_nfhl] ERROR: Could not find ${NFHL_LAYER}.shp in ${SHP_DIR}" >&2
  exit 1
fi

echo "[ingest_nfhl] Ingesting ${SHP_FILE} into flood_zones table..."

ogr2ogr \
  -f "PostgreSQL" \
  PG:"${DATABASE_URL}" \
  "${SHP_FILE}" \
  -nln flood_zones \
  -nlt MULTIPOLYGON \
  -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=geom \
  -lco FID=id \
  -append \
  -progress

echo "[ingest_nfhl] Ingest complete for state FIPS ${STATE_FIPS}."
