# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MapaLinear is a comprehensive travel assistance platform that extracts OpenStreetMap data to create linear maps of Brazilian roads. The system consists of a Python FastAPI backend and a PWA (Progressive Web App) frontend, designed to help drivers and passengers visualize upcoming points of interest during road trips.

## Key Architecture

The project uses a modern full-stack architecture:
- **API Server (FastAPI)**: Handles all business logic, OSM data extraction, asynchronous operations, and POI analysis
- **PWA Frontend (NextJS)**: Progressive Web App that works offline, installs on mobile devices, and provides travel-focused UX
- **CLI Client (Typer)**: Developer and power-user interface for testing and administration

Main components:
- `api/`: FastAPI backend with models, routers, services, and middleware
- `frontend/`: NextJS PWA with offline capabilities, mobile-first design, and travel-focused features
- `mapalinear/cli/`: CLI implementation using Typer and Rich
- `cache/`: Stores OSM data cache and async operation results
- Asynchronous operations: Long-running tasks (OSM searches, map generation) are handled asynchronously with progress tracking

## Common Development Commands

### Setup and Dependencies
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Running the Application
```bash
# Start both API and Frontend (using mprocs) - RECOMMENDED
mprocs

# This will start:
# - Frontend dev server on http://localhost:8000 (with hot reload)
# - API server on http://localhost:8001 (with auto restart)
# - Both services restart automatically on code changes

# Or start services individually:
# API server only (on port 8001)
MAPALINEAR_PORT=8001 poetry run python -m api.run

# Frontend only (on port 8000)
cd frontend && npm run dev -- --port 8000

# Run CLI commands (in another terminal with poetry shell activated)
mapalinear search "Origin, UF" "Destination, UF"
mapalinear generate-map "Origin, UF" "Destination, UF"
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

### Code Quality Tools

#### Backend (Python)
```bash
# Format code with black
poetry run black .

# Sort imports with isort
poetry run isort .

# Type checking with mypy
poetry run mypy .

# Run tests (when available)
poetry run pytest
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
# Test a specific CLI command
mapalinear search "Belo Horizonte, MG" "Ouro Preto, MG" --output-file test-result.json

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

### Frontend (PWA)
- `NEXT_PUBLIC_API_URL`: API endpoint for frontend (default: http://localhost:8001/api)
- `NEXT_PUBLIC_MAP_TILES_URL`: Map tiles provider (default: OpenStreetMap)
- `NEXT_PUBLIC_APP_NAME`: App name for PWA manifest (default: MapaLinear)
- `NEXT_PUBLIC_APP_VERSION`: App version for cache busting
- `NEXT_PUBLIC_VAPID_PUBLIC_KEY`: VAPID key for push notifications
- `PWA_CACHE_VERSION`: Service worker cache version
- `OFFLINE_CACHE_SIZE_MB`: Maximum offline cache size (default: 50)

## Key Design Patterns

1. **Asynchronous Operations**: Long-running tasks return operation IDs immediately, allowing clients to check progress later
2. **Caching Strategy**: Results are cached in JSON format to avoid redundant Overpass API calls
3. **Error Handling**: Comprehensive middleware for API error handling with proper status codes
4. **CLI UX**: Rich terminal UI with progress bars, formatted tables, and clear feedback
5. **PWA Offline-First**: Frontend caches essential data locally for use without internet connection
6. **Mobile-First Design**: UI optimized for mobile usage during travel, with touch-friendly interfaces
7. **Progressive Enhancement**: Core functionality works on all devices, enhanced features on modern browsers

## Important Notes

### Backend
- The project requires internet connection for OpenStreetMap data via Overpass API
- All geographical searches are focused on Brazilian locations (cities must include state abbreviation)
- The API must be running for frontend and CLI to work
- Cache files in `cache/` directory can be safely deleted to force fresh data retrieval

### Frontend PWA
- PWA works offline after initial load and route caching
- Install prompt appears on supported devices for native app-like experience
- Service worker caches map data and route information for offline use
- Background sync updates cached data when connection is restored
- Push notifications can alert users about recommended stops (requires user permission)

### Express instructions from developer
- Just commit code under my request
- Consider the backend and frontend are always running and restarting automatically on code changes
- 