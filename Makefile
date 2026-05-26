.PHONY: help build up down logs generate-data generate-month run-pipeline run-backfill load-month trigger-airflow test test-unit format lint type-check quality clean-data clean-all psql check-health frontend-install frontend-dev

REFERENCE_DATE ?= 2026-01-01
MONTH ?= 2026-04

help:
	@echo "build          Build das imagens Docker"
	@echo "up             Sobe PostgreSQL e Airflow"
	@echo "down           Para todos os servicos"
	@echo "generate-data  Popula 90 dias da camada Raw"
	@echo "generate-month Popula Raw para MONTH=YYYY-MM"
	@echo "run-pipeline   Processa REFERENCE_DATE no DW"
	@echo "run-backfill   Processa os 90 dias iniciais no DW"
	@echo "load-month     Processa MONTH=YYYY-MM no DW"
	@echo "trigger-airflow Dispara a DAG para REFERENCE_DATE=YYYY-MM-DD"
	@echo "quality        Executa formatacao, lint, tipos e testes"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

generate-data:
	docker compose run --rm airflow-scheduler python -m scripts.generate_sales_data --start-date 2026-01-01 --days 90

generate-month:
	docker compose exec airflow-scheduler python -m scripts.generate_sales_data --month $(MONTH)

run-pipeline:
	docker compose run --rm airflow-scheduler python -m scripts.run_pipeline $(REFERENCE_DATE)

run-backfill:
	docker compose run --rm airflow-scheduler python -m scripts.backfill --start-date 2026-01-01 --days 90

load-month:
	docker compose exec airflow-scheduler python -m scripts.backfill --month $(MONTH)

trigger-airflow:
	docker compose exec airflow-scheduler airflow dags unpause etl_vendas_fpa
	docker compose exec airflow-scheduler airflow dags trigger -e $(REFERENCE_DATE) etl_vendas_fpa

test:
	python -m pytest --cov=scripts --cov-report=term-missing

test-unit:
	python -m pytest tests/unit

format:
	python -m black config scripts dags app_vendas api tests

lint:
	python -m ruff check config scripts dags app_vendas api tests

type-check:
	python -m mypy config scripts app_vendas api

quality: format lint type-check test

clean-data:
	powershell -NoProfile -Command "Remove-Item -Recurse -Force data/bronze,data/silver,data/gold,data/quarantine,data/logs -ErrorAction SilentlyContinue"

clean-all:
	powershell -NoProfile -Command "Remove-Item -Recurse -Force data/raw,data/bronze,data/silver,data/gold,data/quarantine,data/logs -ErrorAction SilentlyContinue"

psql:
	docker compose exec postgres_dw sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

check-health:
	docker compose ps

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev
