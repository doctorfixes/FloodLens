-- Create the flood_zones table to store FEMA National Flood Hazard Layer data
CREATE TABLE IF NOT EXISTS flood_zones (
    id            BIGSERIAL PRIMARY KEY,
    fld_ar_id     TEXT         NOT NULL,          -- FEMA flood area identifier
    dfirm_id      TEXT         NOT NULL,          -- Digital FIRM panel ID
    version_id    TEXT,                            -- FIRM version identifier
    fld_zone      TEXT         NOT NULL,           -- FEMA flood zone designation (e.g., AE, X, VE)
    zone_subty    TEXT,                            -- Zone sub-type
    sfha_tf       BOOLEAN      NOT NULL DEFAULT FALSE,  -- Special Flood Hazard Area flag
    static_bfe    NUMERIC(8,2),                   -- Static base flood elevation (feet)
    depth         NUMERIC(6,2),                   -- Depth in feet (for Zone AO/AH)
    len_unit      TEXT,                            -- Unit of measurement
    velocity      NUMERIC(8,2),                   -- Velocity (ft/s, for Zone AO)
    ar_revert     TEXT,                            -- AR revert zone
    ar_subtrv     TEXT,                            -- AR sub-revert zone
    bfe_revert    NUMERIC(8,2),                   -- BFE revert value
    dep_revert    NUMERIC(8,2),                   -- Depth revert value
    study_typ     TEXT,                            -- Study type
    eff_date      DATE,                            -- Effective date of FIRM panel
    source        TEXT,                            -- Data source
    geom          GEOMETRY(MULTIPOLYGON, 4326) NOT NULL  -- Spatial geometry in WGS84
);
