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
# Optional env:   NFHL_EFF_DATE - ISO effective date to stamp onto imported rows
# Required tools: ogr2ogr (GDAL >= 3.4), psql

set -euo pipefail

SHP_FILE="${1:?Arg 1 required: path to .shp file}"
STATE_FIPS="${2:?Arg 2 required: two-digit state FIPS code}"
LOG_DIR="./logs"
LOG_FILE="${LOG_DIR}/ingest_$(date +%Y%m%d_%H%M%S)_state${STATE_FIPS}.log"
DB_URL="${SUPABASE_DB_URL:?SUPABASE_DB_URL environment variable is not set}"
NFHL_EFF_DATE="${NFHL_EFF_DATE:-}"
STAGING_TABLE="nfhl_import_${STATE_FIPS}_$$"

if [[ ! "${STATE_FIPS}" =~ ^[0-9]{2}$ ]]; then
  echo "STATE_FIPS must be a two-digit FIPS code" >&2
  exit 1
fi

if [[ ! -f "${SHP_FILE}" ]]; then
  echo "Shapefile not found: ${SHP_FILE}" >&2
  exit 1
fi

if [[ -n "${NFHL_EFF_DATE}" && ! "${NFHL_EFF_DATE}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "NFHL_EFF_DATE must be an ISO date in YYYY-MM-DD format" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "${LOG_FILE}"
}

cleanup() {
  psql "${DB_URL}" -v ON_ERROR_STOP=1 -q -c \
    "DROP TABLE IF EXISTS public.${STAGING_TABLE};" >/dev/null 2>&1 || true
}
trap cleanup EXIT

log "START - State FIPS: ${STATE_FIPS}"
log "Source file: ${SHP_FILE}"
log "Effective date override: ${NFHL_EFF_DATE:-NONE}"

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
  -nln "public.${STAGING_TABLE}" \
  \
  -overwrite \
  \
  -lco GEOMETRY_NAME=geometry \
  \
  --config PG_USE_COPY YES \
  \
  -skipfailures \
  \
  2>&1 | tee -a "${LOG_FILE}"

STAGING_COUNT=$(psql "${DB_URL}" -t -c \
  "SELECT COUNT(*) FROM public.${STAGING_TABLE};" \
  2>/dev/null | tr -d ' ' || echo "QUERY FAILED")
log "Rows staged for state ${STATE_FIPS}: ${STAGING_COUNT}"

psql "${DB_URL}" -v ON_ERROR_STOP=1 \
  -v state_fips="${STATE_FIPS}" \
  -v nfhl_eff_date="${NFHL_EFF_DATE}" \
  -v staging_table="public.${STAGING_TABLE}" <<'SQL' 2>&1 | tee -a "${LOG_FILE}"
INSERT INTO public.flood_zones (
  geometry,
  dfirm_id,
  source_feature_id,
  panel_number,
  m_zone_code,
  zone_subtype,
  bfe,
  static_bfe,
  depth,
  velocity,
  eff_date,
  source_citation,
  state_fips,
  county_fips
)
SELECT
  ST_Multi(geometry)::geometry(MultiPolygon, 4326) AS geometry,
  dfirm_id,
  fld_ar_id AS source_feature_id,
  NULL::text AS panel_number,
  fld_zone AS m_zone_code,
  NULLIF(zone_subty, ' ') AS zone_subtype,
  NULLIF(static_bfe, -9999)::numeric(8,2) AS bfe,
  NULLIF(static_bfe, -9999)::numeric(8,2) AS static_bfe,
  NULLIF(depth, -9999)::numeric(8,2) AS depth,
  NULLIF(velocity, -9999)::numeric(8,2) AS velocity,
  NULLIF(:'nfhl_eff_date', '')::date AS eff_date,
  source_cit AS source_citation,
  :'state_fips'::char(2) AS state_fips,
  CASE
    WHEN length(dfirm_id) >= 5 THEN substring(dfirm_id from 1 for 5)::char(5)
    ELSE NULL::char(5)
  END AS county_fips
FROM :staging_table
WHERE geometry IS NOT NULL
  AND dfirm_id IS NOT NULL
  AND fld_ar_id IS NOT NULL
  AND fld_zone IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM public.flood_zones existing
    WHERE existing.state_fips = :'state_fips'::char(2)
      AND existing.source_feature_id = fld_ar_id
      AND existing.eff_date IS NOT DISTINCT FROM NULLIF(:'nfhl_eff_date', '')::date
  );
SQL

# Count rows in DB for this state after ingestion.
POST_COUNT=$(psql "${DB_URL}" -t -c \
  "SELECT COUNT(*) FROM public.flood_zones WHERE state_fips = '${STATE_FIPS}';" \
  2>/dev/null | tr -d ' ' || echo "QUERY FAILED")

log "Rows in DB for state ${STATE_FIPS} after ingestion: ${POST_COUNT}"
log "END"
