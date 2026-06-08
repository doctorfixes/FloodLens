CREATE TABLE IF NOT EXISTS public.flood_zones (
  id              BIGSERIAL PRIMARY KEY,

  -- Spatial geometry column. SRID 4326 enforced at column level.
  -- All source data must be reprojected to 4326 before insert.
  -- ogr2ogr handles this via -t_srs EPSG:4326.
  geometry        GEOMETRY(MultiPolygon, 4326) NOT NULL,

  -- FEMA NFHL source columns. Field names match the .dbf attribute table.
  dfirm_id        TEXT         NOT NULL,    -- DFIRM panel identifier e.g. "12086C"
  panel_number    TEXT,                     -- Full panel number e.g. "12086C0465"
  m_zone_code     TEXT         NOT NULL,    -- Zone code e.g. "AE", "X", "VE"
  bfe             NUMERIC(8,2),             -- Base Flood Elevation in feet NAVD88
  static_bfe      NUMERIC(8,2),             -- Static BFE where no profile exists
  depth           NUMERIC(8,2),             -- Depth in Zone AO areas
  velocity        NUMERIC(8,2),             -- Velocity in Zone AO areas
  eff_date        DATE,                     -- Panel effective date
  source_citation TEXT,                     -- FEMA citation string

  -- Ingestion metadata. Not sourced from FEMA.
  state_fips      CHAR(2),                  -- Two-digit state FIPS e.g. "12"
  county_fips     CHAR(5),                  -- Five-digit county FIPS e.g. "12086"
  ingested_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Supporting indexes for panel-level refresh and zone filtering.
-- Do not add the GIST spatial index here -- it runs in 00002b with CONCURRENTLY.
CREATE INDEX IF NOT EXISTS idx_flood_zones_dfirm_id
  ON public.flood_zones (dfirm_id);

CREATE INDEX IF NOT EXISTS idx_flood_zones_m_zone_code
  ON public.flood_zones (m_zone_code);

CREATE INDEX IF NOT EXISTS idx_flood_zones_state_fips
  ON public.flood_zones (state_fips);

CREATE INDEX IF NOT EXISTS idx_flood_zones_county_fips
  ON public.flood_zones (county_fips);
