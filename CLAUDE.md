# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MapaLinear is a Python FastAPI + CLI application that extracts OpenStreetMap data to create linear maps of Brazilian roads. It allows users to search for routes between cities, generate linear maps with points of interest (gas stations, toll booths, restaurants, cities), and manage asynchronous operations.

## Key Architecture

The project uses a client-server architecture:
- **API Server (FastAPI)**: Handles all business logic, OSM data extraction, and asynchronous operations
- **CLI Client (Typer)**: Provides a user-friendly interface that communicates with the API

Main components:
- `api/`: FastAPI backend with models, routers, services, and middleware
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
# Start the API server (using mprocs)
mprocs

# Or start the API server directly
python -m api.run

# Run CLI commands (in another terminal with poetry shell activated)
mapalinear search "Origin, UF" "Destination, UF"
mapalinear generate-map "Origin, UF" "Destination, UF"
```

### Code Quality Tools
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

### Testing a Single Feature
```bash
# Test a specific CLI command
mapalinear search "Belo Horizonte, MG" "Ouro Preto, MG" --output-file test-result.json

# Check API directly
curl http://localhost:8000/api/health
```

## Environment Variables

- `MAPALINEAR_API_URL`: API endpoint (default: http://localhost:8000/api)
- `MAPALINEAR_HOST`: API host (default: 0.0.0.0)
- `MAPALINEAR_PORT`: API port (default: 8000)

## Key Design Patterns

1. **Asynchronous Operations**: Long-running tasks return operation IDs immediately, allowing clients to check progress later
2. **Caching Strategy**: Results are cached in JSON format to avoid redundant Overpass API calls
3. **Error Handling**: Comprehensive middleware for API error handling with proper status codes
4. **CLI UX**: Rich terminal UI with progress bars, formatted tables, and clear feedback

## Important Notes

- The project requires internet connection for OpenStreetMap data via Overpass API
- All geographical searches are focused on Brazilian locations (cities must include state abbreviation)
- The API must be running for CLI commands to work
- Cache files in `cache/` directory can be safely deleted to force fresh data retrieval