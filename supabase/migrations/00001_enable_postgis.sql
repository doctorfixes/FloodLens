-- Enable PostGIS and topology extensions.
-- Must be the first migration. All spatial tables and functions depend on this.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
