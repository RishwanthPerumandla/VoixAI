.PHONY: help up down build restart logs seed clean ps

# Default target
help: ## Show this help message
	@echo "VoixAI - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Build and start all services (daemon mode)
	docker compose up --build -d

build: ## Build all Docker images without starting
	docker compose build

down: ## Stop all services
	docker compose down

restart: ## Rebuild and restart all services
	docker compose up --build -d

logs: ## Tail logs from all services
	docker compose logs -f

logs-api: ## Tail API logs
	docker compose logs -f api

logs-agent: ## Tail agent runtime logs
	docker compose logs -f agent-runtime

logs-web: ## Tail web app logs
	docker compose logs -f web

logs-livekit: ## Tail LiveKit server logs
	docker compose logs -f livekit

seed: ## Seed demo data (first time only)
	docker compose exec api python -c "from seed import seed; seed()"

ps: ## Show running containers
	docker compose ps

clean: ## Remove containers, volumes, and images
	docker compose down -v --rmi all

health: ## Check service health
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "API: not healthy"
	@curl -s http://localhost:3000 > /dev/null && echo "Web: healthy" || echo "Web: not healthy"
	@curl -s http://localhost:7880 > /dev/null && echo "LiveKit: healthy" || echo "LiveKit: not healthy"

token: ## Test token generation
	@curl -s -X POST http://localhost:8000/api/livekit/token \
		-H "Content-Type: application/json" \
		-d '{"room_name":"voixai-mvp-demo","participant_name":"web-user"}' | python -m json.tool
