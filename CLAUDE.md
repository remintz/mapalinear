# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MapaLinear is a comprehensive travel assistance platform that creates linear maps of Brazilian roads using multiple geographic data providers. The system consists of a Python FastAPI backend and a PWA (Progressive Web App) frontend, designed to help drivers and passengers visualize upcoming points of interest during road trips.

The platform operates in two distinct modes:
1. **Map Generation (online)**: Fetches data from selected geographic providers and generates linear maps
2. **Trip Tracking (offline)**: Uses GPS with previously downloaded data for offline navigation

## Key Architecture

The project uses a modern full-stack architecture with multi-provider geographic data support:
- **API Server (FastAPI)**: Handles all business logic, geographic data extraction, asynchronous operations, and POI analysis
- **Geographic Providers**: Pluggable system supporting OSM, HERE Maps, TomTom, and others
- **PWA Frontend (NextJS)**: Progressive Web App that works offline, installs on mobile devices, and provides travel-focused UX

Main components:
- `api/`: FastAPI backend with models, routers, services, and middleware
- `api/providers/`: Multi-provider geographic data abstraction layer (see PRD)
- `api/database/`: SQLAlchemy 2.0 async models and repositories (PostgreSQL)
- `frontend/`: NextJS PWA with offline capabilities, mobile-first design, and travel-focused features
- `docs/`: Technical documentation including PRDs
- Asynchronous operations: Long-running tasks (data searches, map generation) are handled asynchronously with progress tracking

### API Routers

The API is organized into the following routers (registered in `api/main.py`):

**Core Functionality:**
- `auth_router` (`/api/auth`): Authentication endpoints (Google OAuth, JWT tokens, user info)
- `operations_router` (`/api/operations`): Async operation management (create, poll status)
- `maps_router` (`/api/maps`): Saved maps management (list, get, export PDF, adopt, delete, regenerate)
- `export` (`/api/export`): Map export functionality

**Administration:**
- `admin_router` (`/api/admin`): User management, impersonation, database stats, maintenance
- `admin_pois_router` (`/api/admin/pois`): POI management and statistics (admin only)
- `settings_router` (`/api/settings`): System settings management
- `api_logs_router` (`/api/api-logs`): API call logs and cost monitoring
- `application_logs_router` (`/api/application-logs`): Application logs from database
- `frontend_errors_router` (`/api/frontend-errors`): Frontend error logging and retrieval

**Data Management:**
- `municipalities_router` (`/api/municipalities`): Municipalities/cities data
- `problem_types_router` (`/api/problem-types`): Problem type definitions
- `problem_reports_router` (`/api/reports`): User problem reports with attachments
- `poi_debug_router` (`/api/poi-debug`): POI debugging and analysis tools

**Analytics & Monitoring:**
- `session_activity_router` (`/api/session-activity`): User session tracking
- `user_events_router` (`/api/user-events`): User event logging and analytics

### Authentication System
- **Google OAuth**: Users authenticate via Google ID token
- **JWT tokens**: Backend issues JWT for session management
- **Admin impersonation**: Admins can impersonate users for support
- Key files: `api/routers/auth_router.py`, `api/services/auth_service.py`, `api/middleware/auth.py`

### Database Migrations (Alembic)
```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```
Migrations are in `api/database/migrations/versions/`

## Common Development Commands

### Setup and Dependencies
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### PostgreSQL Setup

**Quick Start:** When using `mprocs` (recommended), PostgreSQL is automatically started. Then initialize the database:

```bash
# Start all services (including PostgreSQL)
mprocs

# In another terminal, initialize the database (first time only)
make db-setup

# If you have issues with the database, recreate it:
make db-recreate
```

If you want to run PostgreSQL manually:

```bash
# Using Docker (recommended for development)
docker run --name mapalinear-postgres \
  -e POSTGRES_DB=mapalinear \
  -e POSTGRES_USER=mapalinear \
  -e POSTGRES_PASSWORD=mapalinear \
  -v mapalinear-pgdata:/var/lib/postgresql/data \
  -p 5432:5432 \
  -d postgres:16

# Or install PostgreSQL locally
# macOS:
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian:
sudo apt-get install postgresql-16
sudo systemctl start postgresql

# Create database and user (for local installation)
psql -U postgres -c "CREATE DATABASE mapalinear;"
psql -U postgres -c "CREATE USER mapalinear WITH PASSWORD 'mapalinear';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE mapalinear TO mapalinear;"

# Initialize the schema (required before first run)
make db-setup
```

### Running the Application
```bash
# Start all services (using mprocs) - RECOMMENDED
mprocs

# This will start:
# - PostgreSQL database (Docker container with persistent volume)
# - Frontend dev server on http://localhost:8000 (with hot reload)
# - API server on http://localhost:8001 (with auto restart)
# - All services restart automatically on code changes

# Or start services individually:
# API server only (on port 8001)
MAPALINEAR_PORT=8001 poetry run python -m api.run

# Frontend only (on port 8000)
cd frontend && npm run dev -- --port 8000
```

### Frontend Development (POC)
```bash
# Setup frontend (first time only)
cd frontend
npm install

# Start development server with hot reload
npm run dev

# Build for production with PWA optimization
npm run build

# Start production server
npm start

# Test PWA features locally
npm run start:https  # Serves with HTTPS for PWA testing
```

### Database Management (Makefile)

**IMPORTANT:** You must run `make db-setup` before starting the application for the first time. The application will NOT automatically create the database schema.

```bash
# Show all available commands
make help

# Container management
make db-start      # Start PostgreSQL container
make db-stop       # Stop PostgreSQL container
make db-recreate   # Recreate container from scratch (clears all data)

# Database setup
make db-setup      # Initialize database (create DB, user, and schema)
make db-reset      # Reset database completely

# Cache management
make db-stats      # View cache statistics
make db-clear      # Clear all cache entries
make db-cleanup    # Remove expired entries only

# Utilities
make db-shell      # Open PostgreSQL interactive shell

# Other useful commands
make install    # Install dependencies
make run        # Start all services with mprocs
make format     # Format code (black + isort)
make test       # Run tests with coverage check (min 52%)
```

### Code Quality Tools

#### Backend (Python)
```bash
# Format code with black
poetry run black .

# Sort imports with isort
poetry run isort .

# Type checking with mypy
poetry run mypy .

# Run tests with coverage (minimum 52% required)
poetry run python -m pytest --cov=api --cov-fail-under=52

# Run specific test file
poetry run python -m pytest tests/services/test_road_service.py -v
```

#### Frontend (TypeScript/React)
```bash
# In frontend/ directory
cd frontend

# Lint code with ESLint
npm run lint

# Fix linting issues automatically
npm run lint:fix

# Type checking with TypeScript
npm run type-check

# Run tests
npm run test

# Run tests in watch mode
npm run test:watch

# Check PWA compliance
npm run lighthouse
```

### Testing a Single Feature

#### Backend Testing
```bash
# Check API directly
curl http://localhost:8001/api/health

# Test new POI search endpoint
curl "http://localhost:8001/api/pois/search?lat=-23.5505&lon=-46.6333&radius=1000&types=gas_station,restaurant"

# Test route statistics
curl "http://localhost:8001/api/roads/stats?origin=São Paulo, SP&destination=Rio de Janeiro, RJ"
```

#### Frontend/PWA Testing
```bash
# Test PWA in mobile simulation
npm run dev:mobile

# Test offline functionality
npm run test:offline

# Test install prompt
npm run test:install

# Performance audit
npm run lighthouse:perf
```

## Environment Variables

### Backend (API)
- `MAPALINEAR_API_URL`: API endpoint (default: http://localhost:8001/api)
- `MAPALINEAR_HOST`: API host (default: 0.0.0.0)
- `MAPALINEAR_PORT`: API port (default: 8001)

### Cache System (PostgreSQL)
- `POSTGRES_HOST`: PostgreSQL host (default: localhost)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_DATABASE`: PostgreSQL database name (default: mapalinear)
- `POSTGRES_USER`: PostgreSQL user (default: mapalinear)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: mapalinear)
- `POSTGRES_POOL_MIN_SIZE`: Minimum connection pool size (default: 10)
- `POSTGRES_POOL_MAX_SIZE`: Maximum connection pool size (default: 20)

### API Call Logging (Cost Monitoring)

All external API calls (OSM, HERE, Google Places) are logged to the database for cost monitoring and analysis.

**Logged Information:**
- Provider (osm, here, google_places)
- Operation type (geocode, poi_search, route, etc.)
- Endpoint URL and HTTP method
- Response status and duration
- Response size in bytes
- Result count
- Cache hit/miss status
- Error messages (if any)

**API Endpoints:**
- `GET /api/api-logs/stats` - Aggregated statistics by provider and operation
- `GET /api/api-logs/stats/daily` - Daily call statistics for trend analysis
- `GET /api/api-logs/recent` - Recent API call logs for debugging
- `GET /api/api-logs/errors` - API calls with errors for troubleshooting
- `DELETE /api/api-logs/cleanup` - Remove old logs (default: keep 90 days)

**Key Files:**
- `api/database/models/api_call_log.py` - Database model
- `api/database/repositories/api_call_log.py` - Repository for queries
- `api/services/api_call_logger.py` - Logging service with batched writes
- `api/routers/api_logs_router.py` - API endpoints for statistics

### Geographic Providers (Multi-Provider System)

**Provider Selection (per operation):**
- `POI_PROVIDER`: Provider for POI search (osm, here) - default: osm
- `HERE_API_KEY`: HERE Maps API key (required when using HERE for POIs)

**Note:** Route calculation always uses OSM (OSRM). In the future, HERE routing may be added.

**OSM Configuration:**
- `OSM_OVERPASS_ENDPOINT`: Custom Overpass API endpoint (default: https://overpass-api.de/api/interpreter)
- `OSM_NOMINATIM_ENDPOINT`: Custom Nominatim endpoint (default: https://nominatim.openstreetmap.org)

**Cache TTLs:**
- `GEO_CACHE_TTL_GEOCODE`: Cache TTL for geocoding (default: 604800 seconds / 7 days)
- `GEO_CACHE_TTL_ROUTE`: Cache TTL for routes (default: 21600 seconds / 6 hours)
- `GEO_CACHE_TTL_POI`: Cache TTL for POIs (default: 86400 seconds / 1 day)
- `GEO_CACHE_TTL_POI_DETAILS`: Cache TTL for POI details (default: 43200 seconds / 12 hours)

### POI Enrichment Configuration

The system supports enriching POIs with data from multiple sources. Each enrichment is independently configurable:

**Google Places Enrichment (ratings for restaurants/hotels):**
- `GOOGLE_PLACES_API_KEY`: Google Places API key for fetching ratings
- `GOOGLE_PLACES_ENABLED`: Enable Google Places enrichment (default: true)
- `GOOGLE_PLACES_CACHE_TTL`: Cache TTL for Google Places data (default: 2592000 seconds / 30 days per Google ToS)

**HERE Maps Enrichment (phone, website, opening hours, structured address):**
- `HERE_ENRICHMENT_ENABLED`: Enable HERE enrichment for OSM POIs (default: false)
- `HERE_API_KEY`: HERE Maps API key (required when enabled)

**Note:** HERE enrichment only applies when `POI_PROVIDER=osm`. When `POI_PROVIDER=here`, POIs already contain HERE data natively.

### Frontend (PWA)
- `NEXT_PUBLIC_API_URL`: API endpoint for frontend (default: http://localhost:8001/api)
- `NEXT_PUBLIC_MAP_TILES_URL`: Map tiles provider (default: OpenStreetMap)
- `NEXT_PUBLIC_APP_NAME`: App name for PWA manifest (default: MapaLinear)
- `NEXT_PUBLIC_APP_VERSION`: App version for cache busting
- `NEXT_PUBLIC_VAPID_PUBLIC_KEY`: VAPID key for push notifications
- `PWA_CACHE_VERSION`: Service worker cache version
- `OFFLINE_CACHE_SIZE_MB`: Maximum offline cache size (default: 50)

## Key Design Patterns

1. **Multi-Provider Architecture**: Pluggable geographic data providers with unified interface (OSM, HERE Maps, TomTom)
2. **Provider Abstraction**: Business logic independent of specific geographic data source
3. **Unified Caching**: Intelligent cache system that works across all providers with semantic matching
4. **Asynchronous Operations**: Long-running tasks return operation IDs immediately, allowing clients to check progress later
5. **Error Handling**: Comprehensive middleware for API error handling with proper status codes
6. **PWA Offline-First**: Frontend caches essential data locally for use without internet connection
7. **Mobile-First Design**: UI optimized for mobile usage during travel, with touch-friendly interfaces
8. **Progressive Enhancement**: Core functionality works on all devices, enhanced features on modern browsers

## Critical Technical Details

### Cache System Architecture

The Unified Cache (`api/providers/cache.py`) is critical for performance and cost optimization. It now uses **PostgreSQL** as the default backend for persistence and scalability.

**Key Classes:**
- `CacheKey`: Generates consistent cache keys with parameter normalization
  - Coordinates rounded to 3 decimal places (~111m precision)
  - Strings normalized (lowercase, trimmed)
  - Lists sorted for consistency
- `CacheEntry`: Stores cached data with metadata and expiration
  - Handles JSON serialization of Pydantic models, Enums, tuples, sets
  - Implements `_serialize_data()` for robust type conversion
  - Implements `_reconstruct_data()` to rebuild Pydantic objects on load
- `UnifiedCache`: Main cache interface with intelligent matching
  - **Exact matching**: Hash-based lookup for identical parameters via PostgreSQL primary key
  - **Semantic matching**: For geocoding with similar addresses
  - **Spatial matching**: For POI searches in nearby locations
  - **Persistence**: Stored in PostgreSQL database with connection pooling
  - **Automatic cleanup**: Expired entries removed periodically

**Database Schema:**
- Table: `cache_entries` with JSONB columns for flexible data storage
- Indexes on: expires_at, operation, provider, params (GIN index)
- Schema file: `api/providers/cache_schema.sql`

**Cache Hit Criteria:**
- **Geocoding/Reverse Geocoding**: Exact match on normalized address or coordinates
- **POI Search**: Either exact match OR spatial match (distance < avg radius && same categories)
- **Routes**: Exact match on origin/destination coordinates and waypoints

**Backend:**
- The cache always uses PostgreSQL for persistence and reliability
- PostgreSQL connection pooling configured via environment variables
- Tests should use unique parameters to avoid cache collisions

**Important:**
- When modifying cache logic, ensure `_serialize_data()` handles all Pydantic model types to avoid "not JSON serializable" errors
- PostgreSQL database must be running and accessible for the cache to work
- Use Docker or local PostgreSQL installation (see setup instructions below)

### Provider System

Located in `api/providers/`, follows factory pattern:

**Structure:**
- `base.py`: Abstract `GeoProvider` interface that all providers must implement
- `models.py`: Unified Pydantic models (`GeoLocation`, `Route`, `POI`, `POICategory`)
- `manager.py`: Provider factory with singleton pattern
- `osm/provider.py`: OpenStreetMap implementation (Nominatim, Overpass API, OSRM)
- `here/provider.py`: HERE Maps implementation

**Adding a new provider:**
1. Create new directory under `api/providers/`
2. Implement `GeoProvider` abstract methods
3. Register in `manager.py`
4. Add configuration to `settings.py`

**Provider methods all providers must implement:**
- `geocode(address)`: Address → coordinates
- `reverse_geocode(lat, lon, poi_name?)`: Coordinates → address
- `calculate_route(origin, destination, waypoints?, avoid?)`: Route calculation
- `search_pois(location, radius, categories, limit)`: Find POIs
- `get_poi_details(poi_id)`: Get detailed POI info

### Map Generation Pipeline

The map generation process consists of multiple steps, each with configurable data sources:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAP GENERATION PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. GEOCODING (origin/destination)                                          │
│     └── Provider: OSM (Nominatim) - always                                  │
│                                                                             │
│  2. ROUTE CALCULATION                                                       │
│     └── Provider: OSM (OSRM) - always                                       │
│                                                                             │
│  3. POI SEARCH (along route)                                                │
│     └── Provider: Configurable via POI_PROVIDER (osm or here)               │
│     └── OSM: Free, community data, may lack contact info                    │
│     └── HERE: Paid API, better names/phones/addresses                       │
│                                                                             │
│  4. GOOGLE PLACES ENRICHMENT (optional)                                     │
│     └── Enabled via: GOOGLE_PLACES_ENABLED=true                             │
│     └── Adds: ratings, review counts for restaurants/hotels                 │
│     └── Cost: ~$17-35 per 1000 requests                                     │
│                                                                             │
│  5. HERE ENRICHMENT (optional, only when POI_PROVIDER=osm)                  │
│     └── Enabled via: HERE_ENRICHMENT_ENABLED=true                           │
│     └── Adds: phone, website, opening hours, structured address             │
│     └── Cost: Free tier 250k/month, then ~$0.50-5 per 1000 requests         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Configuration Matrix:**

| POI_PROVIDER | GOOGLE_PLACES_ENABLED | HERE_ENRICHMENT_ENABLED | Result |
|--------------|----------------------|-------------------------|--------|
| osm          | true                 | false                   | OSM POIs + Google ratings |
| osm          | true                 | true                    | OSM POIs + Google ratings + HERE contact info |
| osm          | false                | true                    | OSM POIs + HERE contact info |
| here         | true                 | N/A (ignored)           | HERE POIs + Google ratings |
| here         | false                | N/A (ignored)           | HERE POIs only |

**Important:** These are SYSTEM-LEVEL configurations (environment variables). In the future, user-level preferences will be added that affect only map VISUALIZATION, not data fetching.

**Services involved (modular architecture):**

**Map Generation Services:**
- `api/services/road_service.py`: Main map generation orchestrator (~500 lines)
- `api/services/poi_search_service.py`: POI search and junction calculation (~400 lines)
- `api/services/poi_quality_service.py`: POI quality assessment and filtering (~100 lines)
- `api/services/route_segmentation_service.py`: Route segmentation (~40 lines)
- `api/services/route_statistics_service.py`: Route statistics and recommendations (~80 lines)
- `api/services/milestone_factory.py`: Milestone creation from POIs (~90 lines)
- `api/services/junction_calculation_service.py`: Junction/entroncamento calculation for distant POIs
- `api/services/segment_service.py`: Route segment management and reuse

**Data Enrichment Services:**
- `api/services/google_places_service.py`: Google Places enrichment (ratings)
- `api/services/here_enrichment_service.py`: HERE Maps enrichment (contact info)

**Storage & Assembly Services:**
- `api/services/map_storage_service_db.py`: Map persistence to database
- `api/services/map_assembly_service.py`: Assembling maps from segments and POIs
- `api/services/poi_persistence_service.py`: POI persistence and deduplication

**Infrastructure Services:**
- `api/services/async_service.py`: Async operations lifecycle management
- `api/services/auth_service.py`: Authentication and JWT token management
- `api/services/api_call_logger.py`: API call logging for cost monitoring
- `api/services/database_log_handler.py`: Database logging handler
- `api/services/log_cleanup_service.py`: Automated log cleanup service
- `api/services/database_maintenance_service.py`: Database maintenance operations
- `api/services/user_event_logger.py`: User event tracking and logging

**Utility & Support Services:**
- `api/services/poi_debug_service.py`: POI debugging data collection
- `api/services/audio_service.py`: Audio file processing (for problem reports)
- `api/services/image_service.py`: Image file processing (for problem reports)

**Utility modules:**
- `api/utils/geo_utils.py`: Pure geographic calculations (Haversine, interpolation)
- `api/utils/async_utils.py`: Async execution utilities
- `api/utils/export_utils.py`: PDF export utilities

**Database model:**
- `api/database/models/poi.py`: POI model supports multi-provider data
  - `primary_provider`: Which provider created the POI (osm, here)
  - `osm_id`, `here_id`: Provider-specific IDs
  - `here_data`: JSONB field for HERE-specific structured data
  - `enriched_by`: List of enrichment sources applied

### Async Operations Pattern

Long-running operations use async tasks stored in PostgreSQL:

**Flow:**
1. API endpoint starts async task → returns operation_id immediately
2. Client polls `/api/operations/{operation_id}` for status
3. Operation updates progress in database
4. On completion, result stored in database
5. Frontend shows progress bar during polling
6. Old completed/failed operations are automatically cleaned up

**Key files:**
- `api/services/async_service.py`: Manages async operations lifecycle
- `api/database/models/async_operation.py`: Database model
- `api/database/repositories/async_operation.py`: Repository with CRUD operations

**Cleanup:**
- Stale in_progress operations (>2 hours) are marked as failed
- Completed/failed operations older than 24 hours are automatically removed

### Database Models Overview

The system uses SQLAlchemy 2.0 with async support. Key models and their relationships:

**Core Domain Models:**
- `User`: User accounts (Google OAuth, admin flags, timestamps)
- `Map`: Linear maps between locations (origin, destination, segments as JSONB, metadata)
- `UserMap`: Junction table for user-map associations (many-to-many, supports map sharing)
- `POI`: Points of interest (multi-provider support: osm_id, here_id, primary_provider, enriched_by)
- `RouteSegment`: Reusable route segments (geometry, metadata, versioning)
- `SegmentPOI`: POIs associated with route segments (many-to-many)
- `MapSegment`: Segments associated with a specific map
- `MapPOI`: POIs associated with a specific map (with junction data, distance from route)

**Operational Models:**
- `AsyncOperation`: Long-running async operations (status, progress, result)
- `CacheEntry`: Unified cache entries (provider, operation, params, data, TTL)
- `GooglePlacesCache`: Google Places API response cache
- `ApiCallLog`: External API call logging (provider, operation, status, duration, cost tracking)
- `ApplicationLog`: Application logs stored in database
- `FrontendErrorLog`: Frontend error logs from users

**Administrative Models:**
- `SystemSettings`: Key-value system configuration
- `ProblemType`: Problem type definitions for user reports
- `ProblemReport`: User problem reports with status tracking
- `ReportAttachment`: File attachments for problem reports (images, audio)
- `ImpersonationSession`: Admin user impersonation sessions
- `POIDebugData`: Debug data for POI analysis

**Analytics Models:**
- `UserEvent`: User event tracking (event_type, category, metadata)
- `EventTypes`: Event type definitions and categorization

**Model Relationships:**
- User ↔ UserMap ↔ Map (many-to-many: users can have multiple maps, maps can belong to multiple users)
- Map → MapSegment → RouteSegment (maps contain segments, segments can be reused)
- Map → MapPOI → POI (maps have POIs, POIs can appear in multiple maps)
- RouteSegment → SegmentPOI → POI (segments have POIs, POIs can appear in multiple segments)
- User → ProblemReport → ProblemType (users create reports of specific types)
- ProblemReport → ReportAttachment (reports can have multiple attachments)

**Repository Pattern:**
All models have corresponding repositories in `api/database/repositories/` that provide async CRUD operations and custom queries. Repositories extend `BaseRepository` for common operations.

## Important Notes

### Backend
- The project requires internet connection for geographic data from selected provider (OSM, HERE, etc.)
- All geographical searches are focused on Brazilian locations (cities must include state abbreviation)
- The API must be running for frontend to work
- Geographic provider is selected via `GEO_PRIMARY_PROVIDER` environment variable
- **PostgreSQL database must be running and initialized** for the cache system to work
- Database schema must be initialized with `make db-setup` before first run
- Unified cache works across all providers with intelligent key generation
- Cache data persists in PostgreSQL with connection pooling for optimal performance

### Frontend PWA
- PWA works offline after initial load and route caching
- Install prompt appears on supported devices for native app-like experience
- Service worker caches map data and route information for offline use
- Background sync updates cached data when connection is restored
- Push notifications can alert users about recommended stops (requires user permission)

### Logging System

The system has multiple logging layers for different purposes:

**File Logging:**
- **Main log**: `logs/app.log` - rotating file handler (10MB max, 3 backups)
- **Operation logs**: `logs/mapalinear_YYYYMMDD_HHMMSS.log` - per-operation logs for debugging specific map generation runs
- Configuration: `api/config/logging_config.yaml`
- Debug mode: Use `api/config/logging_config.debug.yaml` for verbose output

**Database Logging:**
- **Application Logs**: Stored in `application_logs` table via `DatabaseLogHandler`
  - Logs are batched and written asynchronously for performance
  - Accessible via `/api/application-logs` endpoints
  - Automatic cleanup via `LogCleanupService` (runs every 24h)
- **API Call Logs**: External API calls logged to `api_call_logs` table
  - Tracks provider, operation, status, duration, bytes, cache hits
  - Used for cost monitoring and analysis
  - Accessible via `/api/api-logs` endpoints
  - Default retention: 90 days
- **Frontend Error Logs**: Client-side errors logged to `frontend_error_logs` table
  - Includes error message, stack trace, user agent, user ID
  - Accessible via `/api/frontend-errors` endpoints (admin only)
- **User Events**: User actions logged to `user_events` table
  - Tracks event types, categories, metadata
  - Used for analytics and usage tracking
  - Accessible via `/api/user-events` endpoints

**Log Correlation:**
- Request IDs are generated per request and included in all logs
- Session IDs from frontend are captured and stored
- User emails are included in log context when authenticated
- Logs can be correlated using request_id and session_id fields

**Key Files:**
- `api/config/logging_config.yaml`: Logging configuration
- `api/config/logging_setup.py`: Logging initialization
- `api/services/database_log_handler.py`: Database log handler
- `api/services/log_cleanup_service.py`: Automated cleanup service
- `api/services/api_call_logger.py`: API call logging service
- `api/services/user_event_logger.py`: User event logging service

### Express instructions from developer
- Just commit code under my request
- Consider the backend and frontend are always running and restarting automatically on code changes

## Technical Documentation

### PRDs (Product Requirements Documents)
- **Multi-Provider Refactoring**: `docs/PRD-MultiProvider-GeoAPI-Refactoring.md`
  - Complete specification for multi-provider geographic data architecture
  - Defines interfaces, cache system, and implementation roadmap
  - Status: APPROVED - Ready for implementation
- **User Analytics**: `docs/PRD-User-Analytics.md`
  - Audit logging and usage statistics system
  - Tracks user behavior, device types, feature usage
  - Status: APPROVED - Ready for implementation

### Development Guidelines for Multi-Provider System
When working with geographic data:
1. Always use the provider abstraction layer (`api/providers/`)
2. Never directly import OSM-specific libraries in business logic
3. Use unified models (Pydantic) for all geographic data
4. Leverage the unified cache system for performance
5. Test with multiple providers when implementing new features
6. Maintain >90% test coverage for provider-related code

### Test-Driven Development (TDD)
- IMPORTANTE: Implemente usando Test Driven Development (TDD)
- os testes automáticos devem sempre passar 100%
- se um teste automático está falhando descubra a causa raiz. O objetivo não é simplesmente passar nos testes mas assegurar que o sistema está funcionando conforme desejado
- só faça commit se eu pedir
- Cobertura mínima de testes: 52% (enforced via `make test`)

### Test Structure
```
tests/
  services/
    test_road_service.py              # Integration tests for map generation
    test_poi_search_service.py        # POI search and side determination
    test_poi_quality_service.py       # Quality scoring and filtering
    test_route_segmentation_service.py # Route segmentation
    test_route_statistics_service.py  # Statistics and recommendations
    test_milestone_factory.py         # Milestone creation
  utils/
    test_geo_utils.py                 # Geographic calculations (Haversine, etc.)
    test_async_utils.py               # Async utilities
  providers/
    test_osm_provider.py              # OSM provider tests
    test_cache.py                     # Cache system tests
```

**Running tests:**
```bash
# All tests with coverage
make test

# Specific test file
poetry run python -m pytest tests/services/test_poi_search_service.py -v

# Specific test class
poetry run python -m pytest tests/services/test_poi_quality_service.py::TestIsPOIAbandoned -v
```

## Common Pitfalls & Solutions

### Cache Serialization Issues
**Problem:** "Object of type X is not JSON serializable"
**Solution:** Update `CacheEntry._serialize_data()` to handle the new type. Already handles:
- Pydantic models (via `.model_dump()`)
- Enums (via `.value`)
- Tuples/sets → lists
- Bytes → base64

### Provider Rate Limiting
**Problem:** OSM Overpass API returns 429 (Too Many Requests)
**Solution:**
- Ensure `_wait_before_request()` is called before each request
- Check `_query_delay` (default 1 second between requests)
- Consider switching to HERE Maps provider for high-volume usage

### Coordinate Precision in Cache
**Problem:** Cache miss for nearly identical coordinates
**Solution:** Coordinates are rounded to 3 decimal places (~111m) in cache keys. This is intentional for cache efficiency. If exact precision needed, check normalized params in cache logs.

### POI Name Issues
**Problem:** POI comes from OSM without proper name (shows category instead)
**Solution:** OSM data limitation. Many POIs lack names. Code handles this in `_parse_osm_element_to_poi()` with fallback to amenity type.

### PostgreSQL Cache Management
**Problem:** Need to clear cache or reset database
**Solution:**

Using Makefile (recommended):
```bash
make db-clear    # Clear all cache entries
make db-stats    # View cache statistics
make db-cleanup  # Remove expired entries
make db-reset    # Reset entire database
```

Or using Docker directly:
```bash
# Clear all cache entries (keeps database structure)
docker exec -it mapalinear-postgres psql -U mapalinear -c "DELETE FROM cache_entries;"

# Or reset entire database and volume
docker stop mapalinear-postgres
docker rm mapalinear-postgres
docker volume rm mapalinear-pgdata
# Next mprocs start will create fresh database

# View cache statistics
docker exec -it mapalinear-postgres psql -U mapalinear -c "SELECT COUNT(*), operation FROM cache_entries GROUP BY operation;"
```

### PostgreSQL Connection Issues
**Problem:** "Connection refused" or "could not connect to server"
**Solution:**
- Ensure Docker is running: `docker ps`
- Check if PostgreSQL container is healthy: `docker logs mapalinear-postgres`
- Verify port 5432 is not in use: `lsof -i :5432`
- For local PostgreSQL conflicts, stop local instance or change port in `.env`
