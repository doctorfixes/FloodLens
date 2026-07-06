# ZoneCheck — Queued Backlog / Session Handoff

Snapshot of outstanding work, queued for a future session. Written 2026-07-05.

## Where things stand

- **Test coverage + CI** were just added in **PR #24** (branch
  `claude/test-coverage-analysis-lm8c90`): Deno tests for the production
  `zonecheck` function, a Python `pytest` suite (`tests/python/`), and a pgTAP
  suite for `fn_get_flood_risk` (`tests/sql/`), all wired into
  `.github/workflows/test.yml` (3 jobs). **Check whether #24 is merged before
  building on it.**
- Two loader bugs were fixed in #24 — `scripts/load_fema_data.py` `escape()`
  (stop doubling backslashes) and `is_valid_bfe()` (`> -9999`). If you are
  reading this on a branch off `main` where those still look unfixed, it just
  means #24 hasn't merged yet. Do **not** redo them.
- **Data is Denver-only.** The sole loaded dataset is
  `supabase/migrations/00004_load_denver_flood_zones.sql` (~2,348 features,
  bbox `-105.1..-104.9 / 39.6..39.8`). Any address outside Denver returns
  `unmapped: true, determination: null`. Today this is a Denver pilot, not a
  national service.

## Prioritized backlog

1. **[Highest] Add a `/v1/zonecheck` Zuplo gateway route.**
   `zuplo/zuplo.json` only routes the **legacy** `/v1/determine-zone`, so the
   production Edge Function has no API-key auth, rate limiting, or billing in
   front of it. Add a zonecheck route rewriting to
   `${env.SUPABASE_FUNCTION_URL}/zonecheck` with the same inbound policies
   (`api-key`, `rate-limit`, `request-validation`) and the stripe outbound
   policy. Consider deprecating the determine-zone route.

2. **Prove multi-state NFHL ingestion beyond Denver.**
   Validate `scripts/ingest_nfhl.sh` (ogr2ogr path) and/or
   `scripts/load_fema_data.py` (REST path) for at least one additional state;
   confirm rows land and `fn_get_flood_risk` returns correct results outside
   Denver. Note `load_fema_data.py`'s bounding box + `SUPABASE_PROJECT_REF`
   are currently hard-coded to Denver.

3. **Validate / deploy the Airflow quarterly refresh DAG.**
   `dags/nfhl_refresh_dag.py` is marked "planned"; target states FL/TX/CA/NY/LA
   have no data yet. It is not deployed or run end-to-end.

4. **Wire and test Stripe metered billing.**
   `zuplo/policies/stripe-metered-billing.ts` is attached only to the legacy
   route, marked "planned", and untested. Wire it to zonecheck and add tests.

5. **Test the Verixio bridge internals.**
   `lookupNeighborhoodRisk` network/timeout path and the `Deno.Kv` cache
   hit/miss/null logic in `supabase/functions/zonecheck/index.ts` are
   uncovered (only the handler wiring is tested). Needs a small refactor to
   make the cache injectable/testable.

6. **Finish the determine-zone → zonecheck rename retirement.**
   Once the gateway and callers are migrated, retire the legacy function,
   route, and deploy workflow.

## Suggested sequencing

Do **1** first (the production function currently has nothing in front of it),
then **2** to move past the Denver-only limitation, then **3–6** as the data
layer and billing stabilize.
