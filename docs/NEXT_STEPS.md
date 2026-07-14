# ZoneCheck — Remaining Backlog

Updated 2026-07-14.

## What's done

- **Test coverage + CI** — Deno (handler + geocoder), Python (validation,
  fema_client, db_client, load_fema_data, DAG decision logic), pgTAP
  (fn_get_flood_risk). All run in `.github/workflows/test.yml`.
- **`/v1/zonecheck` gateway route** — Added to `zuplo/zuplo.json` with
  api-key, rate-limit, request-validation, and stripe-metered-billing policies.
- **Deploy workflows consolidated** — Single `deploy-functions.yml` replaces
  three overlapping workflows; uses `SUPABASE_PROJECT_ID` secret (no hardcoded
  project ref).
- **Bug fixes** — `escape()`, `is_valid_bfe()`, dead-code guard, Deno.Kv
  degradation, Verixio API key header.

## Requires human-provisioned keys

| Secret | Where to set | What breaks without it |
|---|---|---|
| `SUPABASE_ACCESS_TOKEN` | GitHub repo secret | Deploy workflows skip (no deploys on push to main) |
| `SUPABASE_PROJECT_ID` | GitHub repo secret | Same — deploy + migration validation workflows skip |
| `GOOGLE_MAPS_API_KEY` | Supabase Function Secrets | Geocoding fallback disabled; Census failures return 502 |
| `STRIPE_SECRET_KEY` | Zuplo environment variable | Metered billing no-ops (silent, by design) |
| `VERIXIO_URL` | Supabase Function Secrets | Neighborhood risk returns null (graceful degradation) |
| `VERIXIO_API_KEY` | Supabase Function Secrets | Verixio requests fail auth (if the endpoint requires it) |
| `SUPABASE_DB_URL` | Airflow Variable or env | NFHL refresh DAG cannot connect to database |
| `SUPABASE_SERVICE_KEY` | env for `load_fema_data.py` | FEMA loader script cannot execute SQL |

## Remaining code-level backlog

1. **Multi-state NFHL ingestion** — `scripts/load_fema_data.py` is
   Denver-hardcoded (bbox, project ref). Branch `claude/multistate-ingestion`
   has the parameterized version + ON CONFLICT fix. Needs merge decision.

2. **Verixio bridge testability** — `lookupNeighborhoodRisk` in
   `supabase/functions/zonecheck/index.ts` uses module-level Deno.Kv and
   `fetch` directly. Branch `claude/verixio-bridge-tests` refactors to
   injectable deps with 8 tests. Needs merge decision.

3. **Stripe billing tests** — Branch `claude/stripe-billing-tests` extracts
   billing logic into a testable core module with 7 tests. Needs merge
   decision.

4. **Retire `determine-zone`** — Legacy function is structurally identical to
   `zonecheck` minus Verixio. Once callers migrate to `/v1/zonecheck`, remove
   the function, its deploy step, its Zuplo route, and its `config.toml`
   entry.

5. **Hardcoded project ref in `load_fema_data.py`** — Line 28 still has the
   project ref inline. The multi-state branch fixes this; if not merging that
   branch, at minimum move to an env var.
