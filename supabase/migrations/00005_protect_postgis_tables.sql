-- Migration: Enable RLS on all remaining public schema tables
-- The Security Advisor flags any table in the public schema without RLS.
-- PostGIS system tables (spatial_ref_sys, geometry_columns, geography_columns)
-- are read-only reference data, but we enable RLS with SELECT-only policies
-- to satisfy the security scanner and prevent any accidental mutations via
-- the anonymous key.
--
-- The flood_zones table was handled in a separate migration
-- (20250101000003_rls_flood_zones.sql).
--
-- NOTE: geometry_columns and geography_columns are PostGIS views, not tables.
-- They inherit RLS from their underlying tables, so we only need to handle
-- spatial_ref_sys (a real table).

-- Enable RLS on spatial_ref_sys
ALTER TABLE public.spatial_ref_sys ENABLE ROW LEVEL SECURITY;

-- Allow SELECT for all roles (the data is standard reference data)
CREATE POLICY "spatial_ref_sys_select"
  ON public.spatial_ref_sys
  FOR SELECT
  TO public
  USING (true);
