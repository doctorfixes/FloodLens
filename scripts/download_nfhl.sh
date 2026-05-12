#!/usr/bin/env bash
#
# download_nfhl.sh
#
# FEMA MSC download wrapper for a single state NFHL archive.
#
# Usage:   ./scripts/download_nfhl.sh <STATE_FIPS>
# Example: ./scripts/download_nfhl.sh 12
#
# Output: data/state_<STATE_FIPS>/

set -euo pipefail

STATE_FIPS="${1:?Arg 1 required: two-digit state FIPS code}"
DATA_DIR="${DATA_DIR:-data}"
DEST_DIR="${DATA_DIR}/state_${STATE_FIPS}"
ZIP_FILE="${DEST_DIR}/NFHL_${STATE_FIPS}.zip"
DOWNLOAD_URL="https://msc.fema.gov/portal/downloadProduct?productTypeID=NFHL&productSubTypeID=State&productVersionID=${STATE_FIPS}"

mkdir -p "${DEST_DIR}"

echo "[download_nfhl] Downloading NFHL state ${STATE_FIPS}"
curl --fail --silent --show-error --location --retry 3 --retry-delay 5 \
  --output "${ZIP_FILE}" \
  "${DOWNLOAD_URL}"

echo "[download_nfhl] Extracting ${ZIP_FILE}"
unzip -q -o "${ZIP_FILE}" -d "${DEST_DIR}"
rm "${ZIP_FILE}"

echo "[download_nfhl] Done. Shapefiles available in ${DEST_DIR}"
