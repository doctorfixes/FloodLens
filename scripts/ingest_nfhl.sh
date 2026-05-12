#!/usr/bin/env bash
#
# ingest_nfhl.sh
#
# Ingests a single FEMA NFHL state shapefile into the flood_zones table.
# Appends rows. Never truncates. Safe to run multiple times on the same state.
#
# Usage:   ./scripts/ingest_nfhl.sh <shapefile.shp> <STATE_FIPS>
# Example: ./scripts/ingest_nfhl.sh ./data/S_FLD_HAZ_AR_12.shp 12
#
# Required env:   SUPABASE_DB_URL - full postgres:// connection string
# Required tools: ogr2ogr (GDAL >= 3.4), psql

set -euo pipefail

SHP_FILE="${1:?Arg 1 required: path to .shp file}"
STATE_FIPS="${2:?Arg 2 required: two-digit state FIPS code}"
LOG_DIR="./logs"
LOG_FILE="${LOG_DIR}/ingest_$(date +%Y%m%d_%H%M%S)_state${STATE_FIPS}.log"
DB_URL="${SUPABASE_DB_URL:?SUPABASE_DB_URL environment variable is not set}"

mkdir -p "${LOG_DIR}"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "${LOG_FILE}"
}

log "START - State FIPS: ${STATE_FIPS}"
log "Source file: ${SHP_FILE}"

# Log detected source SRS for audit trail.
DETECTED_SRS=$(ogrinfo -al -so "${SHP_FILE}" 2>/dev/null \
  | grep -i "Proj" | head -1 || echo "NOT DETECTED")
log "Detected source projection: ${DETECTED_SRS}"

# Count source features before ingestion.
SRC_COUNT=$(ogrinfo -al -so "${SHP_FILE}" 2>/dev/null \
  | grep "Feature Count" | awk '{print $3}' || echo "UNKNOWN")
log "Source feature count: ${SRC_COUNT}"

ogr2ogr \
  -f "PostgreSQL" \
  PG:"${DB_URL}" \
  "${SHP_FILE}" \
  \
  -t_srs EPSG:4326 \
  \
  -nlt PROMOTE_TO_MULTI \
  \
  -nln public.flood_zones \
  \
  -append \
  \
  -sql "SELECT *, '${STATE_FIPS}' AS state_fips FROM $(basename "${SHP_FILE}" .shp)" \
  \
  --config PG_USE_COPY YES \
  \
  -skipfailures \
  \
  2>&1 | tee -a "${LOG_FILE}"

# Count rows in DB for this state after ingestion.
POST_COUNT=$(psql "${DB_URL}" -t -c \
  "SELECT COUNT(*) FROM public.flood_zones WHERE state_fips = '${STATE_FIPS}';" \
  2>/dev/null | tr -d ' ' || echo "QUERY FAILED")

log "Rows in DB for state ${STATE_FIPS} after ingestion: ${POST_COUNT}"
log "END"
