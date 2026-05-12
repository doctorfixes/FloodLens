-- 1. Miami, FL - should return HIGH risk, zone AE or VE.
SELECT zone_code, zone_label, risk_level, panel_number, eff_date
FROM public.fn_get_flood_risk(25.7617, -80.1918);

-- 2. Denver, CO - should return MINIMAL risk, zone X.
SELECT zone_code, zone_label, risk_level, panel_number, eff_date
FROM public.fn_get_flood_risk(39.7392, -104.9903);

-- 3. Disclaimer field must be non-null on every row.
SELECT disclaimer IS NOT NULL AS disclaimer_present
FROM public.fn_get_flood_risk(25.7617, -80.1918);

-- 4. Confirm spatial index exists and is valid.
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'flood_zones'
  AND indexname = 'idx_flood_zones_geometry';

-- 5. Confirm spatial query performance target.
-- Must show "Execution Time" under 250ms.
EXPLAIN ANALYZE
SELECT * FROM public.fn_get_flood_risk(25.7617, -80.1918);
