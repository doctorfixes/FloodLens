CREATE OR REPLACE FUNCTION public.fn_get_flood_risk(
  p_lat DOUBLE PRECISION,
  p_lng DOUBLE PRECISION
)
RETURNS TABLE (
  zone_code      TEXT,
  zone_label     TEXT,
  risk_level     TEXT,
  insurance_note TEXT,
  bfe            NUMERIC,
  depth          NUMERIC,
  panel_number   TEXT,
  dfirm_id       TEXT,
  eff_date       DATE,
  disclaimer     TEXT
)
LANGUAGE sql
STABLE       -- Result is stable within a single transaction.
PARALLEL SAFE -- Safe for parallel query execution plans.
AS $$
  WITH matched_zone AS (
    SELECT
      fz.m_zone_code,
      fz.zone_subtype,
      fz.bfe,
      fz.static_bfe,
      fz.depth,
      fz.panel_number,
      fz.dfirm_id,
      fz.eff_date,

      -- Risk priority weight for boundary tie-breaking.
      -- When a point falls on the edge of two zones, the higher-risk zone wins.
      -- This is the conservative and legally defensible behavior.
      CASE
        WHEN fz.m_zone_code IN ('VE','V1-30','V')       THEN 1  -- Coastal high hazard
        WHEN fz.m_zone_code IN ('AE','AO','AH','A99')   THEN 2  -- SFHA with BFE
        WHEN fz.m_zone_code = 'A'                       THEN 3  -- SFHA without BFE
        WHEN fz.m_zone_code = 'AR'                      THEN 4  -- Restoration zone
        WHEN fz.m_zone_code = 'D'                       THEN 5  -- Undetermined
        WHEN fz.m_zone_code LIKE 'X%' AND (
          fz.depth > 0
          OR fz.zone_subtype ILIKE '%0.2 PCT%'
          OR fz.zone_subtype ILIKE '%0.2 PERCENT%'
          OR fz.zone_subtype ILIKE '%DEPTH LESS THAN 1 FOOT%'
          OR fz.zone_subtype ILIKE '%DRAINAGE AREA LESS THAN 1 SQUARE MILE%'
          OR fz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NON-ACCREDITED LEVEE%'
          OR fz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NONACCREDITED LEVEE%'
          OR fz.zone_subtype ILIKE '%FUTURE CONDITIONS%'
          OR fz.zone_subtype ILIKE '%FUTURE CONDITONS%'
        ) THEN 6  -- Shaded X (500-year)
        WHEN fz.m_zone_code = 'X'                       THEN 7  -- Unshaded X (minimal)
        ELSE 99
      END AS risk_priority

    FROM public.flood_zones fz
    WHERE ST_Covers(
      fz.geometry,
      -- ST_MakePoint(longitude, latitude) -- X axis then Y axis.
      -- Reversing this is a silent failure that returns wrong or empty results.
      ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)
    )
    ORDER BY risk_priority ASC
    LIMIT 1
  )
  SELECT
    mz.m_zone_code AS zone_code,

    CASE
      WHEN mz.m_zone_code IN ('VE','V1-30','V')
        THEN 'Coastal High Hazard Area'
      WHEN mz.m_zone_code IN ('AE','AO','AH','A99','A')
        THEN 'Special Flood Hazard Area (SFHA)'
      WHEN mz.m_zone_code = 'AR'
        THEN 'Special Flood Hazard Area - Restoration Zone'
      WHEN mz.m_zone_code = 'D'
        THEN 'Undetermined Risk Area'
      WHEN mz.m_zone_code LIKE 'X%' AND (
        mz.depth > 0
        OR mz.zone_subtype ILIKE '%0.2 PCT%'
        OR mz.zone_subtype ILIKE '%0.2 PERCENT%'
        OR mz.zone_subtype ILIKE '%DEPTH LESS THAN 1 FOOT%'
        OR mz.zone_subtype ILIKE '%DRAINAGE AREA LESS THAN 1 SQUARE MILE%'
        OR mz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NON-ACCREDITED LEVEE%'
        OR mz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NONACCREDITED LEVEE%'
        OR mz.zone_subtype ILIKE '%FUTURE CONDITIONS%'
        OR mz.zone_subtype ILIKE '%FUTURE CONDITONS%'
      )
        THEN 'Moderate Flood Hazard Area (500-Year)'
      WHEN mz.m_zone_code = 'X'
        THEN 'Minimal Flood Hazard Area'
      ELSE 'Zone ' || mz.m_zone_code
    END AS zone_label,

    CASE
      WHEN mz.m_zone_code IN ('VE','V1-30','V','AE','AO','AH','A99','A','AR')
        THEN 'HIGH'
      WHEN mz.m_zone_code LIKE 'X%' AND (
        mz.depth > 0
        OR mz.zone_subtype ILIKE '%0.2 PCT%'
        OR mz.zone_subtype ILIKE '%0.2 PERCENT%'
        OR mz.zone_subtype ILIKE '%DEPTH LESS THAN 1 FOOT%'
        OR mz.zone_subtype ILIKE '%DRAINAGE AREA LESS THAN 1 SQUARE MILE%'
        OR mz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NON-ACCREDITED LEVEE%'
        OR mz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NONACCREDITED LEVEE%'
        OR mz.zone_subtype ILIKE '%FUTURE CONDITIONS%'
        OR mz.zone_subtype ILIKE '%FUTURE CONDITONS%'
      )
        THEN 'MODERATE'
      WHEN mz.m_zone_code = 'X'
        THEN 'MINIMAL'
      WHEN mz.m_zone_code = 'D'
        THEN 'UNDETERMINED'
      ELSE 'UNKNOWN'
    END AS risk_level,

    CASE
      WHEN mz.m_zone_code IN ('VE','V1-30','V')
        THEN 'High Risk - Coastal. Flood insurance REQUIRED for federally backed mortgages. Mandatory purchase requirement applies.'
      WHEN mz.m_zone_code IN ('AE','AO','AH','A99','A','AR')
        THEN 'High Risk. Flood insurance REQUIRED for federally backed mortgages. Mandatory purchase requirement applies.'
      WHEN mz.m_zone_code LIKE 'X%' AND (
        mz.depth > 0
        OR mz.zone_subtype ILIKE '%0.2 PCT%'
        OR mz.zone_subtype ILIKE '%0.2 PERCENT%'
        OR mz.zone_subtype ILIKE '%DEPTH LESS THAN 1 FOOT%'
        OR mz.zone_subtype ILIKE '%DRAINAGE AREA LESS THAN 1 SQUARE MILE%'
        OR mz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NON-ACCREDITED LEVEE%'
        OR mz.zone_subtype ILIKE '%FLOOD HAZARD DUE TO NONACCREDITED LEVEE%'
        OR mz.zone_subtype ILIKE '%FUTURE CONDITIONS%'
        OR mz.zone_subtype ILIKE '%FUTURE CONDITONS%'
      )
        THEN 'Moderate Risk (500-Year Floodplain). Flood insurance is recommended but not federally required.'
      WHEN mz.m_zone_code = 'X'
        THEN 'Minimal Risk. Outside the 500-Year floodplain. Flood insurance is optional.'
      WHEN mz.m_zone_code = 'D'
        THEN 'Risk undetermined. FEMA has not studied this area. Consult your local floodplain administrator.'
      ELSE 'Zone not mapped. Contact the local floodplain administrator for an official determination.'
    END AS insurance_note,

    COALESCE(mz.bfe, mz.static_bfe) AS bfe,
    mz.depth,
    mz.panel_number,
    mz.dfirm_id,
    mz.eff_date,

    -- Disclaimer is mandatory. It must appear in every response row without exception.
    'This result is derived from FEMA National Flood Hazard Layer (NFHL) data and is provided for informational purposes only. It does not constitute an official flood zone determination, a Letter of Map Amendment (LOMA), or legal advice. Official determinations must be obtained through a licensed flood determination company or FEMA directly. Data currency depends on NFHL update cadence and may not reflect the most recent map revisions.'::TEXT AS disclaimer

  FROM matched_zone mz;
$$;

-- Grant execute access to Supabase default roles when they are present.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    GRANT EXECUTE ON FUNCTION public.fn_get_flood_risk(DOUBLE PRECISION, DOUBLE PRECISION)
      TO anon;
  END IF;

  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT EXECUTE ON FUNCTION public.fn_get_flood_risk(DOUBLE PRECISION, DOUBLE PRECISION)
      TO authenticated;
  END IF;
END;
$$;
