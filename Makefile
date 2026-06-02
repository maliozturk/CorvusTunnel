# CorvusTunnel — Makefile
# ──────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := up

APP_NAME := corvustunnel
REGISTRY ?= corvustunnel/corvustunnel
VERSION  ?= latest

.PHONY: up down restart logs shell prod publish clean help

up: ## Build and start containers
	docker compose up --build -d

down: ## Stop and remove containers
	docker compose down

restart: down up ## Rebuild and restart

logs: ## Tail container logs
	docker compose logs -f

shell: ## Open shell in running container
	docker exec -it $(APP_NAME) /bin/bash

prod: ## Build production (obfuscated) image
	docker build -f Dockerfile.prod -t $(REGISTRY):$(VERSION) .

publish: ## Build, verify, and push production image
	bash scripts/publish.sh $(VERSION)

clean: down ## Stop containers and remove dangling images
	docker image prune -f

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
