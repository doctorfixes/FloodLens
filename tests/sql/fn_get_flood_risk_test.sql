-- pgTAP tests for public.fn_get_flood_risk(p_lat, p_lng).
--
-- Exercises the zone -> risk_level / zone_label / insurance_note mapping, the
-- coastal-V regex, shaded-X detection (via both zone_subtype and depth), the
-- bfe COALESCE, overlap tie-breaking, and the no-match case.
--
-- Run with pg_prove against a database that has postgis + pgtap installed and
-- the flood_zones table + fn_get_flood_risk function loaded. All fixtures are
-- inserted inside the transaction and rolled back by finish()/ROLLBACK.

BEGIN;
SELECT plan(18);

-- ── Fixtures ────────────────────────────────────────────────────────────────
-- Small non-overlapping envelopes; each test point sits at the envelope centre.
-- ST_Multi wraps the POLYGON envelope into the MultiPolygon the column requires.

INSERT INTO public.flood_zones (dfirm_id, m_zone_code, zone_subtype, bfe, static_bfe, depth, geometry)
VALUES
  -- AE: high-risk SFHA with BFE.
  ('TEST_AE', 'AE', NULL, 452.0, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.91, 39.69, -104.89, 39.71, 4326))),

  -- X (unshaded): minimal risk.
  ('TEST_X', 'X', NULL, NULL, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.81, 39.59, -104.79, 39.61, 4326))),

  -- Shaded X via zone_subtype: 500-year / moderate.
  ('TEST_XS', 'X', '0.2 PCT ANNUAL CHANCE FLOOD HAZARD', NULL, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.71, 39.49, -104.69, 39.51, 4326))),

  -- Shaded X via depth > 0: 500-year / moderate (distinct code path).
  ('TEST_XD', 'X', NULL, NULL, NULL, 1.5,
   ST_Multi(ST_MakeEnvelope(-104.66, 39.44, -104.64, 39.46, 4326))),

  -- VE: coastal high hazard.
  ('TEST_VE', 'VE', NULL, NULL, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.61, 39.39, -104.59, 39.41, 4326))),

  -- D: undetermined.
  ('TEST_D', 'D', NULL, NULL, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.51, 39.29, -104.49, 39.31, 4326))),

  -- V13: numbered coastal zone matched by the regex ^V([1-9]|...)$.
  ('TEST_V13', 'V13', NULL, NULL, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.26, 39.04, -104.24, 39.06, 4326))),

  -- AE with bfe NULL but static_bfe present -> COALESCE should surface 100.
  ('TEST_BFE', 'AE', NULL, NULL, 100.0, NULL,
   ST_Multi(ST_MakeEnvelope(-104.31, 39.09, -104.29, 39.11, 4326))),

  -- Overlap pair: AE and X both cover (39.20, -104.40). AE (priority 2) must win.
  ('TEST_OVL_AE', 'AE', NULL, NULL, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.41, 39.19, -104.39, 39.21, 4326))),
  ('TEST_OVL_X', 'X', NULL, NULL, NULL, NULL,
   ST_Multi(ST_MakeEnvelope(-104.41, 39.19, -104.39, 39.21, 4326)));

-- ── AE (high-risk SFHA) ─────────────────────────────────────────────────────
SELECT is(
  (SELECT zone_code FROM public.fn_get_flood_risk(39.70, -104.90)),
  'AE', 'AE point returns zone_code AE');
SELECT is(
  (SELECT risk_level FROM public.fn_get_flood_risk(39.70, -104.90)),
  'HIGH', 'AE point is HIGH risk');
SELECT is(
  (SELECT zone_label FROM public.fn_get_flood_risk(39.70, -104.90)),
  'Special Flood Hazard Area (SFHA)', 'AE point labelled SFHA');
SELECT ok(
  (SELECT insurance_note FROM public.fn_get_flood_risk(39.70, -104.90))
    LIKE '%REQUIRED%',
  'AE insurance_note flags mandatory purchase');

-- ── X unshaded (minimal) ────────────────────────────────────────────────────
SELECT is(
  (SELECT risk_level FROM public.fn_get_flood_risk(39.60, -104.80)),
  'MINIMAL', 'Unshaded X is MINIMAL risk');
SELECT is(
  (SELECT zone_label FROM public.fn_get_flood_risk(39.60, -104.80)),
  'Minimal Flood Hazard Area', 'Unshaded X labelled minimal');

-- ── Shaded X (moderate) — both detection paths ──────────────────────────────
SELECT is(
  (SELECT risk_level FROM public.fn_get_flood_risk(39.50, -104.70)),
  'MODERATE', 'Shaded X (zone_subtype) is MODERATE risk');
SELECT is(
  (SELECT zone_label FROM public.fn_get_flood_risk(39.50, -104.70)),
  'Moderate Flood Hazard Area (500-Year)', 'Shaded X labelled 500-year');
SELECT is(
  (SELECT risk_level FROM public.fn_get_flood_risk(39.45, -104.65)),
  'MODERATE', 'Shaded X (depth > 0) is MODERATE risk');

-- ── VE / numbered V (coastal high hazard) ───────────────────────────────────
SELECT is(
  (SELECT risk_level FROM public.fn_get_flood_risk(39.40, -104.60)),
  'HIGH', 'VE point is HIGH risk');
SELECT is(
  (SELECT zone_label FROM public.fn_get_flood_risk(39.40, -104.60)),
  'Coastal High Hazard Area', 'VE point labelled coastal high hazard');
SELECT is(
  (SELECT risk_level FROM public.fn_get_flood_risk(39.05, -104.25)),
  'HIGH', 'Numbered V zone (V13) matched by regex is HIGH risk');
SELECT is(
  (SELECT zone_label FROM public.fn_get_flood_risk(39.05, -104.25)),
  'Coastal High Hazard Area', 'V13 labelled coastal high hazard');

-- ── D (undetermined) ────────────────────────────────────────────────────────
SELECT is(
  (SELECT risk_level FROM public.fn_get_flood_risk(39.30, -104.50)),
  'UNDETERMINED', 'Zone D is UNDETERMINED risk');

-- ── bfe COALESCE ────────────────────────────────────────────────────────────
SELECT is(
  (SELECT bfe FROM public.fn_get_flood_risk(39.10, -104.30)),
  100.0::numeric, 'bfe falls back to static_bfe when bfe is NULL');

-- ── Overlap tie-breaking (higher risk wins) ─────────────────────────────────
SELECT is(
  (SELECT zone_code FROM public.fn_get_flood_risk(39.20, -104.40)),
  'AE', 'Overlapping AE + X returns the higher-risk AE zone');

-- ── Disclaimer always present ───────────────────────────────────────────────
SELECT ok(
  (SELECT disclaimer FROM public.fn_get_flood_risk(39.70, -104.90))
    LIKE 'This result is derived from FEMA National Flood Hazard Layer%',
  'Every determination row carries the FEMA disclaimer');

-- ── No match -> zero rows ───────────────────────────────────────────────────
SELECT is_empty(
  $$ SELECT * FROM public.fn_get_flood_risk(10.0, 10.0) $$,
  'A point outside every mapped polygon returns no rows');

SELECT * FROM finish();
ROLLBACK;
