.DEFAULT_GOAL := help

COMPOSE ?= docker compose
SERVICE ?=
WORKERS ?= 2
RATE ?= 100
DURATION ?= 30s

.PHONY: help up down stop build ps logs test migrate migrate-check scale load docs docs-stop docs-check docs-build docs-export

help:
	@printf '%s\n' \
	  'make up             Запустить проект с пересборкой и дождаться готовности' \
	  'make down           Остановить и удалить контейнеры, сохранив volumes' \
	  'make stop           Остановить контейнеры' \
	  'make build          Собрать образ приложения' \
	  'make ps             Показать состояние контейнеров' \
	  'make logs           Смотреть логи (SERVICE=api или worker)' \
	  'make test           Запустить стек и тесты в Docker' \
	  'make migrate        Применить миграции на работающем стеке' \
	  'make migrate-check  Проверить соответствие моделей схеме БД' \
	  'make scale          Изменить число worker (WORKERS=2, стек уже запущен)' \
	  'make load           Нагрузка на работающий тестовый стек (RATE=100 DURATION=30s)' \
	  'make docs           Запустить LikeC4: http://localhost:5173' \
	  'make docs-stop      Остановить LikeC4' \
	  'make docs-check     Проверить модель LikeC4' \
	  'make docs-build     Собрать сайт в architecture/dist/' \
	  'make docs-export    Экспортировать PNG в architecture/assets/'

up:
	$(COMPOSE) up --build -d --wait

down:
	$(COMPOSE) --profile docs down

stop:
	$(COMPOSE) --profile docs stop

build:
	$(COMPOSE) build api

ps:
	$(COMPOSE) --profile docs ps

logs:
	$(COMPOSE) --profile docs logs --follow --tail=100 $(SERVICE)

test: up
	$(COMPOSE) --profile test build tests
	$(COMPOSE) --profile test run --rm --no-deps tests

migrate:
	$(COMPOSE) run --rm --no-deps migrate alembic upgrade head

migrate-check:
	$(COMPOSE) run --rm --no-deps migrate alembic check

scale:
	$(COMPOSE) up -d --no-deps --scale worker=$(WORKERS) worker

load:
	RATE="$(RATE)" DURATION="$(DURATION)" $(COMPOSE) --profile load run --rm --no-deps load

docs:
	$(COMPOSE) --profile docs up -d --wait architecture

docs-stop:
	$(COMPOSE) --profile docs stop architecture

docs-check:
	$(COMPOSE) --profile docs run --rm --no-deps architecture validate

docs-build:
	$(COMPOSE) --profile docs run --rm --no-deps architecture build -o dist --base ./ --use-hash-history --title 'SIS1 · System Design'

docs-export:
	$(COMPOSE) --profile docs run --rm --no-deps architecture export png -o assets --sequence
