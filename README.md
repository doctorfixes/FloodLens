# ZoneCheck (formerly FloodLens)

ZoneCheck is a serverless API that converts any US address into a **unified property risk profile** — combining FEMA flood zone determination with neighborhood-level risk scoring (NTS, TCS, VGD).

**One POST, two answers:** flood risk from NFHL data + neighbourhood risk from Verixio's Denver parcel-intelligence engine.

## Stack

- Supabase Postgres 17 + PostGIS for NFHL spatial data.
- Supabase Edge Functions (Deno/TypeScript) for geocoding, flood lookup, and Verixio bridge.
- Verixio Rating Engine — Denver parcel intelligence via `by-coordinates` API.
- Zuplo for API keys, rate limits, request validation, and Stripe metered billing (planned).
- Apache Airflow for quarterly FEMA NFHL delta refreshes (planned).
- GDAL `ogr2ogr` for shapefile ingestion.

## API

```bash
curl -X POST "https://YOUR_SUPABASE_PROJECT.supabase.co/functions/v1/zonecheck" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St, Miami, FL 33101"}'
```

Response includes:
- `determination` — FEMA flood zone data (zone code, risk level, BFE, insurance note)
- `neighborhood` — Verixio neighborhood scores (NTS, TCS, VGD) when available

Every response, including errors, includes a FEMA NFHL disclaimer.

## Repository Layout

- `supabase/migrations/` — PostGIS extension, `flood_zones`, spatial index, and lookup function.
- `supabase/functions/zonecheck/` — Unified edge function (geocode → flood lookup → Verixio bridge).
- `supabase/functions/determine-zone/` — Legacy flood-only edge function (no Verixio bridge).
- `scripts/` — NFHL download, ingestion, and spatial validation helpers.
- `zuplo/` — Gateway route and policy configuration (legacy).
- `docs/` — API reference, setup guide, data provenance, and FEMA zone codes.

## Local Development

```bash
# Start Supabase stack
supabase start

# Deploy the zonecheck function
supabase functions deploy zonecheck

# Run Deno tests
deno test --allow-read --allow-net=deno.land,esm.sh tests
```

## Migration from FloodLens

This project was renamed from FloodLens to ZoneCheck. The old `determine-zone` edge function is still deployed for backward compatibility. All new integrations should use `zonecheck` which includes the Verixio neighbourhood risk bridge.

To update existing callers: change the URL path from `/functions/v1/determine-zone` to `/functions/v1/zonecheck`. The request/response format is identical with the addition of the `neighborhood` field.