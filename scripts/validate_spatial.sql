-- validate_spatial.sql
-- Smoke test queries for fn_get_flood_risk
-- Run these after data ingestion to verify the spatial function is working.
--
-- Usage:
--   psql "$DATABASE_URL" -f scripts/validate_spatial.sql

\echo '--- Validating fn_get_flood_risk ---'

-- Test 1: Check PostGIS is installed
\echo 'Test 1: PostGIS version'
SELECT PostGIS_Full_Version();

-- Test 2: Verify flood_zones table has data
\echo 'Test 2: Row count in flood_zones'
SELECT COUNT(*) AS total_zones FROM flood_zones;

-- Test 3: Check spatial index exists
\echo 'Test 3: Spatial index on flood_zones'
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'flood_zones'
  AND indexdef ILIKE '%gist%';

-- Test 4: Query a known SFHA point (New Orleans, LA — Zone AE)
\echo 'Test 4: Known SFHA point — New Orleans, LA (should return AE zone)'
SELECT *
FROM fn_get_flood_risk(29.9511, -90.0715);

-- Test 5: Query a known low-risk point (Denver, CO — typically Zone X)
\echo 'Test 5: Known low-risk point — Denver, CO (should return X zone)'
SELECT *
FROM fn_get_flood_risk(39.7392, -104.9903);

-- Test 6: Verify SFHA flag logic
\echo 'Test 6: SFHA flag check — any AE/VE zones should have sfha_tf = true'
SELECT
  fld_zone,
  sfha_tf,
  COUNT(*) AS zone_count
FROM flood_zones
WHERE fld_zone IN ('AE', 'VE', 'AO', 'AH', 'A')
GROUP BY fld_zone, sfha_tf
ORDER BY fld_zone;

\echo '--- Validation complete ---'
