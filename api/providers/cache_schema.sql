-- Schema for PostgreSQL cache system
-- This schema stores geographic data cache with intelligent matching capabilities

CREATE TABLE IF NOT EXISTS cache_entries (
    -- Primary key: hash of provider + operation + normalized params
    key TEXT PRIMARY KEY,

    -- Cached data stored as JSONB for efficient querying
    data JSONB NOT NULL,

    -- Provider that generated this data
    provider TEXT NOT NULL,

    -- Operation type (geocode, reverse_geocode, route, poi_search, poi_details)
    operation TEXT NOT NULL,

    -- Timestamps for cache management
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,

    -- Hit tracking for cache statistics
    hit_count INTEGER NOT NULL DEFAULT 0,

    -- Original parameters stored as JSONB for semantic/spatial matching
    params JSONB NOT NULL
);

-- Index on expires_at for efficient cleanup of expired entries
CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON cache_entries(expires_at);

-- Index on operation for semantic matching (geocoding, POI search)
CREATE INDEX IF NOT EXISTS idx_cache_operation ON cache_entries(operation);

-- Index on provider for provider-specific queries
CREATE INDEX IF NOT EXISTS idx_cache_provider ON cache_entries(provider);

-- GIN index on params JSONB for fast parameter matching
CREATE INDEX IF NOT EXISTS idx_cache_params ON cache_entries USING GIN (params);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_cache_operation_expires ON cache_entries(operation, expires_at);

-- Table for cache statistics (optional, can be computed on demand)
CREATE TABLE IF NOT EXISTS cache_stats (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    total_entries INTEGER NOT NULL,
    hits INTEGER NOT NULL,
    misses INTEGER NOT NULL,
    sets INTEGER NOT NULL,
    evictions INTEGER NOT NULL,
    hit_rate_percent DECIMAL(5,2) NOT NULL
);
