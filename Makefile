.PHONY: help db-setup db-reset db-clear db-stats db-shell db-start db-stop db-recreate install run test format db-migrate db-migration db-migrate-downgrade db-migrate-history db-migrate-current

# PostgreSQL configuration
DB_HOST ?= localhost
DB_PORT ?= 5432
DB_NAME ?= mapalinear
DB_USER ?= mapalinear
DB_PASSWORD ?= mapalinear

# Docker container name
CONTAINER_NAME = mapalinear-postgres
VOLUME_NAME = mapalinear-pgdata

help: ## Show this help message
	@echo "MapaLinear - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install

run: ## Start all services with mprocs
	mprocs

db-start: ## Start PostgreSQL container (if not running)
	@echo "🚀 Starting PostgreSQL container..."
	@docker start $(CONTAINER_NAME) 2>/dev/null || \
		docker run -d \
			--name $(CONTAINER_NAME) \
			-e POSTGRES_PASSWORD=postgres \
			-e POSTGRES_USER=postgres \
			-v $(VOLUME_NAME):/var/lib/postgresql/data \
			-p $(DB_PORT):5432 \
			postgres:16
	@echo "⏳ Waiting for PostgreSQL to be ready..."
	@sleep 3
	@echo "✅ PostgreSQL is running"

db-stop: ## Stop PostgreSQL container
	@echo "🛑 Stopping PostgreSQL container..."
	@docker stop $(CONTAINER_NAME) || true
	@echo "✅ PostgreSQL stopped"

db-recreate: ## Recreate PostgreSQL container from scratch
	@echo "🔄 Recreating PostgreSQL container..."
	@docker stop $(CONTAINER_NAME) 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) 2>/dev/null || true
	@docker volume rm $(VOLUME_NAME) 2>/dev/null || true
	@echo "✅ Old container and volume removed"
	@$(MAKE) db-start
	@$(MAKE) db-setup

db-setup: ## Initialize database (create DB, user, and schema)
	@echo "🔧 Setting up database..."
	@docker exec -i $(CONTAINER_NAME) psql -U postgres -c "CREATE DATABASE $(DB_NAME);" 2>/dev/null || echo "Database already exists"
	@docker exec -i $(CONTAINER_NAME) psql -U postgres -c "CREATE USER $(DB_USER) WITH PASSWORD '$(DB_PASSWORD)';" 2>/dev/null || echo "User already exists"
	@docker exec -i $(CONTAINER_NAME) psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $(DB_NAME) TO $(DB_USER);" 2>/dev/null || true
	@docker exec -i $(CONTAINER_NAME) psql -U postgres -c "ALTER DATABASE $(DB_NAME) OWNER TO $(DB_USER);" 2>/dev/null || true
	@echo "✅ Database and user created/verified"
	@echo "📋 Initializing cache schema..."
	@cat api/providers/cache_schema.sql | docker exec -i $(CONTAINER_NAME) psql -U $(DB_USER) -d $(DB_NAME)
	@echo "📋 Running Alembic migrations..."
	@poetry run alembic upgrade head
	@echo "✅ Schema initialized"
	@echo "🎉 Database setup complete!"

db-reset: ## Reset database (drop and recreate everything)
	@echo "⚠️  Resetting database..."
	@docker exec -i $(CONTAINER_NAME) psql -U postgres -c "DROP DATABASE IF EXISTS $(DB_NAME);" || true
	@docker exec -i $(CONTAINER_NAME) psql -U postgres -c "DROP USER IF EXISTS $(DB_USER);" || true
	@echo "🔄 Recreating database..."
	@$(MAKE) db-setup

db-clear: ## Clear all cache entries (keep schema)
	@echo "🗑️  Clearing cache entries..."
	@docker exec -i $(CONTAINER_NAME) psql -U $(DB_USER) -d $(DB_NAME) -c "DELETE FROM cache_entries;"
	@echo "✅ Cache cleared"

db-stats: ## Show cache statistics
	@echo "📊 Cache Statistics:"
	@echo ""
	@docker exec -i $(CONTAINER_NAME) psql -U $(DB_USER) -d $(DB_NAME) -c "\
		SELECT \
			operation, \
			COUNT(*) as total_entries, \
			SUM(hit_count) as total_hits, \
			AVG(hit_count)::numeric(10,2) as avg_hits, \
			MIN(created_at) as oldest_entry, \
			MAX(created_at) as newest_entry, \
			COUNT(*) FILTER (WHERE expires_at > NOW()) as valid_entries, \
			COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries \
		FROM cache_entries \
		GROUP BY operation \
		ORDER BY total_entries DESC;"
	@echo ""
	@echo "📈 Overall Statistics:"
	@docker exec -i $(CONTAINER_NAME) psql -U $(DB_USER) -d $(DB_NAME) -c "\
		SELECT \
			COUNT(*) as total_entries, \
			COUNT(*) FILTER (WHERE expires_at > NOW()) as valid_entries, \
			COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries, \
			pg_size_pretty(pg_database_size('$(DB_NAME)')) as database_size \
		FROM cache_entries;"

db-shell: ## Open PostgreSQL shell
	@docker exec -it $(CONTAINER_NAME) psql -U $(DB_USER) -d $(DB_NAME)

db-cleanup: ## Remove expired cache entries
	@echo "🧹 Cleaning up expired entries..."
	@docker exec -i $(CONTAINER_NAME) psql -U $(DB_USER) -d $(DB_NAME) -c "\
		WITH deleted AS (DELETE FROM cache_entries WHERE expires_at <= NOW() RETURNING *) \
		SELECT COUNT(*) as expired_entries_removed FROM deleted;"
	@echo "✅ Cleanup complete"

# Alembic migration commands
db-migrate: ## Run pending database migrations
	@echo "🔄 Running database migrations..."
	poetry run alembic upgrade head
	@echo "✅ Migrations complete"

db-migration: ## Create a new migration (usage: make db-migration msg="description")
	@echo "📝 Creating new migration..."
	poetry run alembic revision --autogenerate -m "$(msg)"
	@echo "✅ Migration created"

db-migrate-downgrade: ## Rollback the last migration
	@echo "⬇️  Rolling back last migration..."
	poetry run alembic downgrade -1
	@echo "✅ Rollback complete"

db-migrate-history: ## Show migration history
	@echo "📜 Migration history:"
	poetry run alembic history --verbose

db-migrate-current: ## Show current migration revision
	@echo "📍 Current migration revision:"
	poetry run alembic current

test: ## Run tests with coverage check (minimum 55%)
	poetry run python -m pytest --cov=api --cov-fail-under=55

format: ## Format code with black and isort
	poetry run black .
	poetry run isort .

lint: ## Run type checking with mypy
	poetry run mypy .
