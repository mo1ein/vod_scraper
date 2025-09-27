.PHONY: build up down logs clean migration-create migration-up migration-down migration-status dev test build-goose

# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Docker commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v
	docker system prune -f

