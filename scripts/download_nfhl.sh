#!/usr/bin/env bash
# download_nfhl.sh — FEMA MSC download helper
# Downloads the NFHL shapefile archive for a given state FIPS code.
#
# Usage: ./download_nfhl.sh <STATE_FIPS>
# Example: ./download_nfhl.sh 06   # California
#
# Requires: curl, unzip
# Output: data/<STATE_FIPS>/  (extracted shapefiles)

set -euo pipefail

STATE_FIPS="${1:?Usage: $0 <STATE_FIPS>}"
DATA_DIR="${DATA_DIR:-data}"
# Allow overriding the NFHL dataset date via environment variable.
# Visit https://hazards.fema.gov/nfhl to find the latest available date.
NFHL_DATE="${NFHL_DATE:-20231001}"

# Zero-pad to 2 digits
STATE_FIPS=$(printf "%02d" "${STATE_FIPS#0}")

DOWNLOAD_URL="https://hazards.fema.gov/NFHL/${STATE_FIPS}/NFHL_${STATE_FIPS}_${NFHL_DATE}.zip"
DEST_DIR="${DATA_DIR}/${STATE_FIPS}"
ZIP_FILE="${DEST_DIR}/NFHL_${STATE_FIPS}.zip"

echo "[download_nfhl] Downloading NFHL for state FIPS ${STATE_FIPS}..."
mkdir -p "${DEST_DIR}"

curl --fail --silent --show-error \
     --retry 3 --retry-delay 5 \
     --location \
     --output "${ZIP_FILE}" \
     "${DOWNLOAD_URL}"

echo "[download_nfhl] Extracting to ${DEST_DIR}..."
unzip -q -o "${ZIP_FILE}" -d "${DEST_DIR}"
rm "${ZIP_FILE}"

echo "[download_nfhl] Done. Shapefiles available in ${DEST_DIR}"
