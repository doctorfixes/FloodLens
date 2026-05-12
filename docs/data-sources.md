# Data Sources

## Primary Source: FEMA National Flood Hazard Layer (NFHL)

FloodLens is powered by the **FEMA National Flood Hazard Layer (NFHL)**, the authoritative federal dataset of flood hazard areas in the United States.

### What is the NFHL?

The NFHL is a GIS database that contains the digital flood hazard information from FEMA's Flood Insurance Rate Maps (FIRMs). It covers:

- Flood hazard zone boundaries (Special Flood Hazard Areas, moderate-risk zones, minimal-risk zones)
- Base Flood Elevations (BFEs)
- Floodways
- Cross-sections and profiles

### Download & Licensing

The NFHL is published by FEMA under public domain and is freely available via:

- **FEMA Map Service Center (MSC):** https://msc.fema.gov/portal/home
- **FEMA NFHL REST API:** https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer

No commercial restrictions apply.

---

## Update Cadence

| Frequency | Description |
|-----------|-------------|
| Quarterly | FloodLens ingests delta updates from the FEMA REST API (panels with `EFF_DATE` newer than the last refresh) |
| On-demand | Individual state shapefiles can be manually re-ingested via `scripts/ingest_nfhl.sh` |

FEMA continually issues updated FIRM panels as counties complete new flood studies. The NFHL is updated roughly weekly on the FEMA servers; FloodLens captures these changes on a quarterly basis.

---

## Coverage Gaps

The NFHL is comprehensive but has known limitations:

| Gap | Details |
|-----|---------|
| **Un-mapped areas** | Some rural areas and tribal lands have not been studied or mapped. The API returns `404 NO_FLOOD_DATA` for these locations. |
| **Outdated panels** | Some FIRM panels have not been restudied in decades. The `effective_date` field in responses shows when the panel was last updated. |
| **Territories** | Coverage for US territories (Puerto Rico, US Virgin Islands, Guam, etc.) is partial. |
| **Coastal erosion** | The NFHL does not model long-term coastal erosion. Zone boundaries represent conditions at the effective date only. |
| **Levee-impacted areas** | Areas behind levees may show Zone X even if the levee has not been certified under 44 CFR 65.10. |

---

## Geocoding

Addresses are resolved to coordinates using a two-tier approach:

1. **US Census Geocoder** (primary): https://geocoding.geo.census.gov/ — Free, no API key required, covers all US addresses.
2. **Google Maps Geocoding API** (fallback): Used when the Census geocoder returns no results. Requires a valid `GOOGLE_MAPS_API_KEY`.

---

## Disclaimer

FloodLens is intended for informational purposes only. Flood zone determinations from this API should **not** be used as a substitute for an official FEMA flood zone determination (Standard Flood Zone Determination Form, SFDF) required for federally regulated lending transactions. Always consult a licensed flood zone determination service or FEMA's official Letter of Map Amendment (LOMA) process for official determinations.
