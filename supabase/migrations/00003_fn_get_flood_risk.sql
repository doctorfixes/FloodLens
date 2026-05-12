-- Function: fn_get_flood_risk
-- Returns flood zone information for a given WGS84 point coordinate.
-- Parameters:
--   p_lat  DOUBLE PRECISION  Latitude in decimal degrees (WGS84)
--   p_lon  DOUBLE PRECISION  Longitude in decimal degrees (WGS84)
-- Returns a table row with the most-specific flood zone that intersects the point.

CREATE OR REPLACE FUNCTION fn_get_flood_risk(
    p_lat DOUBLE PRECISION,
    p_lon DOUBLE PRECISION
)
RETURNS TABLE (
    fld_zone      TEXT,
    zone_subty    TEXT,
    sfha_tf       BOOLEAN,
    static_bfe    NUMERIC,
    depth         NUMERIC,
    eff_date      DATE,
    dfirm_id      TEXT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        fz.fld_zone,
        fz.zone_subty,
        fz.sfha_tf,
        fz.static_bfe,
        fz.depth,
        fz.eff_date,
        fz.dfirm_id
    FROM
        flood_zones fz
    WHERE
        ST_Contains(
            fz.geom,
            ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)
        )
    ORDER BY
        -- Prefer SFHA zones and most recent effective date
        fz.sfha_tf DESC,
        fz.eff_date DESC NULLS LAST
    LIMIT 1;
$$;

-- Grant execute permission to the anonymous and authenticated roles
GRANT EXECUTE ON FUNCTION fn_get_flood_risk(DOUBLE PRECISION, DOUBLE PRECISION)
    TO anon, authenticated;
