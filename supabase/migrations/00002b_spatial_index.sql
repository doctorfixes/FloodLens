-- supabase no transaction
--
-- CONCURRENTLY cannot run inside a transaction block.
-- The "supabase no transaction" directive tells the Supabase CLI
-- to execute this file outside a transaction wrapper.
-- Without this directive the migration will fail at runtime.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flood_zones_geometry
  ON public.flood_zones
  USING GIST (geometry);
