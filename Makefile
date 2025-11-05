.PHONY: help setup start stop restart logs clean test

# Default target
help:
	@echo "Producer AI Agent - Makefile commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  setup      - Initial setup (copy .env, create directories)"
	@echo "  start      - Start all services"
	@echo "  stop       - Stop all services"
	@echo "  restart    - Restart all services"
	@echo "  logs       - Show logs from all services"
	@echo "  logs-api   - Show API gateway logs"
	@echo "  logs-r2r   - Show R2R logs"
	@echo "  logs-n8n   - Show n8n logs"
	@echo "  clean      - Stop and remove all containers and volumes"
	@echo "  health     - Check health of all services"
	@echo "  db-migrate - Run Prisma migrations"
	@echo "  db-shell   - Connect to PostgreSQL shell"
	@echo "  backup     - Backup PostgreSQL database"
	@echo "  test       - Run integration tests"

# Initial setup
setup:
	@echo "Setting up Producer AI Agent..."
	@test -f .env || cp .env.example .env
	@mkdir -p r2r-config n8n-workflows n8n-custom-nodes init-scripts output logs
	@echo "Setup complete! Please edit .env with your configuration."

# Start services
start:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@make health

# Stop services
stop:
	@echo "Stopping all services..."
	docker-compose down

# Restart services
restart:
	@echo "Restarting all services..."
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api-gateway

logs-r2r:
	docker-compose logs -f r2r

logs-n8n:
	docker-compose logs -f n8n

# Clean everything
clean:
	@echo "WARNING: This will remove all containers, volumes, and data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		rm -rf output/* logs/*; \
		echo "Cleanup complete!"; \
	fi

# Health check
health:
	@echo "Checking service health..."
	@echo "\n=== PostgreSQL ==="
	@docker-compose exec -T postgres pg_isready || echo "PostgreSQL is not ready"
	@echo "\n=== Redis ==="
	@docker-compose exec -T redis redis-cli ping || echo "Redis is not ready"
	@echo "\n=== R2R ==="
	@curl -s http://localhost:7272/v2/health | jq . || echo "R2R is not ready"
	@echo "\n=== n8n ==="
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/healthz || echo "n8n is not ready"
	@echo "\n=== API Gateway ==="
	@curl -s http://localhost:8000/health | jq . || echo "API Gateway is not ready"

# Database operations
db-migrate:
	@echo "Running Prisma migrations..."
	npx prisma generate
	npx prisma db push

db-shell:
	docker-compose exec postgres psql -U postgres -d r2r

backup:
	@echo "Backing up PostgreSQL database..."
	@mkdir -p backups
	@docker-compose exec -T postgres pg_dump -U postgres r2r > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup complete!"

# Testing
test:
	@echo "Running integration tests..."
	@echo "\n=== Testing R2R API ==="
	@curl -X POST http://localhost:8000/api/v1/rag/collections \
		-H "Content-Type: application/json" \
		-d '{"name": "test-collection", "description": "Test collection"}' | jq .
	@echo "\n=== Testing Document Ingestion ==="
	@curl -X POST http://localhost:8000/api/v1/rag/ingest \
		-H "Content-Type: application/json" \
		-d '{"documents": [{"content": "Test document", "title": "Test"}]}' | jq .
	@echo "\n=== Testing Search ==="
	@curl -X POST http://localhost:8000/api/v1/rag/search \
		-H "Content-Type: application/json" \
		-d '{"query": "test", "limit": 5}' | jq .
	@echo "\nAll tests complete!"
