-- Enable RLS on the flood_zones table.
-- The FEMA NFHL data is public reference information (same data available freely
-- from FEMA's NFHL web services), but Supabase's security scanner flags any table
-- in the public schema without RLS enabled. This policy allows SELECT for all
-- roles so the fn_get_flood_risk() function (called by anon/authenticated users)
-- continues to work, and direct table queries remain open (matching the public
-- nature of the source data).
ALTER TABLE public.flood_zones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "flood_zones_select"
  ON public.flood_zones
  FOR SELECT
  TO public
  USING (true);