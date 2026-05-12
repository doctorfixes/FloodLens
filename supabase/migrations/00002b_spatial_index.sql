-- no-transaction
-- Create spatial index on flood_zones geometry column
-- Must run outside a transaction block because CREATE INDEX CONCURRENTLY
-- cannot run inside a transaction.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flood_zones_geom
    ON flood_zones USING GIST (geom);
