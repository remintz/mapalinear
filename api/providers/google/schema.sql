-- Schema for Google Places cache
-- Stores POI ratings from Google Places API with different TTLs:
-- - google_place_id: permanent (per Google TOS)
-- - rating data: 30 days max (per Google TOS)

CREATE TABLE IF NOT EXISTS google_places_cache (
    -- Primary key: OSM POI ID (our internal reference)
    osm_poi_id VARCHAR(100) PRIMARY KEY,

    -- Google Place ID - can be cached permanently per Google TOS
    google_place_id VARCHAR(200) NOT NULL,

    -- Rating data - must expire within 30 days per Google TOS
    rating DECIMAL(2,1),                    -- 1.0 to 5.0 stars
    user_rating_count INTEGER,              -- Number of reviews
    google_maps_uri TEXT,                   -- Direct link to Google Maps

    -- Match metadata (for debugging and quality assessment)
    matched_name VARCHAR(500),              -- Name found in Google
    match_distance_meters DECIMAL(10,2),    -- Distance from search point

    -- Search coordinates used (for cache invalidation if needed)
    search_latitude DECIMAL(10,7) NOT NULL,
    search_longitude DECIMAL(10,7) NOT NULL,
    search_name VARCHAR(500),               -- Name used in search

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- 30 days from creation

    -- Constraints
    CONSTRAINT valid_rating CHECK (rating IS NULL OR (rating >= 1.0 AND rating <= 5.0)),
    CONSTRAINT valid_review_count CHECK (user_rating_count IS NULL OR user_rating_count >= 0)
);

-- Index for cleanup of expired entries
CREATE INDEX IF NOT EXISTS idx_google_places_expires
    ON google_places_cache(expires_at);

-- Index for lookup by google_place_id (for refresh operations)
CREATE INDEX IF NOT EXISTS idx_google_places_google_id
    ON google_places_cache(google_place_id);

-- Index for spatial queries (if we need to find cached entries near a location)
CREATE INDEX IF NOT EXISTS idx_google_places_location
    ON google_places_cache(search_latitude, search_longitude);

-- Comment on table
COMMENT ON TABLE google_places_cache IS
    'Cache for Google Places API ratings data. Place IDs can be stored permanently,
     but rating data must be refreshed every 30 days per Google TOS.';
