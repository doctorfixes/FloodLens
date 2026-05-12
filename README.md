# FloodLens

FloodLens is a serverless API that converts any US address into a FEMA flood
zone determination delivered as structured JSON.

## Stack

- Supabase Postgres 15 + PostGIS for NFHL spatial data.
- Supabase Edge Functions (Deno/TypeScript) for geocoding and lookup.
- Zuplo for API keys, rate limits, request validation, and Stripe metered billing.
- Apache Airflow for quarterly FEMA NFHL delta refreshes.
- GDAL `ogr2ogr` for shapefile ingestion.

## API

```bash
curl -X POST "https://YOUR_ZUPLO_GATEWAY/v1/determine-zone" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St, Miami, FL 33101"}'
```

Every response, including errors, includes a FEMA NFHL disclaimer.

## Repository Layout

- `supabase/migrations/` - PostGIS extension, `flood_zones`, spatial index, and lookup function.
- `supabase/functions/determine-zone/` - Edge Function request handler and geocoder chain.
- `scripts/` - NFHL download, ingestion, and spatial validation helpers.
- `dags/` - Airflow quarterly refresh DAG and utilities.
- `zuplo/` - Gateway route and policy configuration.
- `docs/` - API reference, setup guide, data provenance, and FEMA zone codes.

Free-tier keys should apply both `rate-limit-free.ts` for the 50 request/month
quota and `rate-limit-free-burst.ts` for the 10 request/minute spike limit.

## Local Validation

```bash
deno test --allow-read --allow-net=deno.land,esm.sh tests
supabase db push --dry-run
```

Full production validation requires a Supabase project, ingested NFHL state data,
Zuplo API keys, and Stripe metered billing credentials.

Airflow workers should install `dags/requirements.txt` in addition to providing
GDAL/ogr2ogr and psql on the worker PATH. Set the Airflow Variable or
environment variable `FLOODLENS_INGEST_SCRIPT_PATH` if `ingest_nfhl.sh` is not
available at `/opt/airflow/scripts/ingest_nfhl.sh`.
