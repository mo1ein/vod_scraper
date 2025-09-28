.PHONY: build up down purge status logs clean env

# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

help:
	@echo "env"
	@echo "==> Create .env file \n"
	@echo "build"
	@echo "==> Build all containers \n"
	@echo "up"
	@echo "==> Create and start containers \n"
	@echo "down"
	@echo "==> Down container and remove orphans \n"
	@echo "purge"
	@echo "==> Down container and remove orphans and volumes \n"
	@echo "status"
	@echo "==> Show currently running containers \n"
	@echo "logs"
	@echo "==> Show container logs"

env:
	@[ -e ./.env ] || cp -v ./.env.example ./.env
# Docker commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down --remove-orphans

purge:
	docker compose down --remove-orphans --volumes

status:
	docker ps

logs:
	docker compose logs -f
