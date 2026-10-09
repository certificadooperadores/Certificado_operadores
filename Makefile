# =============================================================================
# Certificado_operadores â€” automatizaciÃ³n de tareas (multiplataforma: cmd/bash)
# =============================================================================

.DEFAULT_GOAL := help
.PHONY: help install dev pre-commit-install pre-commit lint format format-check typecheck test check build clean

help: ## Muestra esta ayuda
	@echo Objetivos disponibles:
	@echo   make install        - uv sync
	@echo   make dev            - install + hooks de pre-commit
	@echo   make lint           - Ruff (lint)
	@echo   make format         - Ruff (formato)
	@echo   make format-check   - verifica el formato sin modificar
	@echo   make typecheck      - ty (tipos)
	@echo   make test           - pytest
	@echo   make check          - lint + formato + tipos + pruebas
	@echo   make pre-commit     - hooks sobre todo el repo
	@echo   make build          - uv build
	@echo   make clean          - limpia caches y artefactos

install: ## Sincroniza el entorno virtual e instala dependencias
	uv sync

dev: install pre-commit-install ## Prepara el entorno de desarrollo (sync + hooks)

pre-commit-install: ## Instala los hooks de pre-commit en el repositorio local
	uv run pre-commit install

pre-commit: ## Ejecuta todos los hooks de pre-commit sobre el repositorio
	uv run pre-commit run --all-files

lint: ## Ejecuta Ruff (lint)
	uv run ruff check .

format: ## Formatea el cÃ³digo con Ruff
	uv run ruff format .

format-check: ## Verifica el formato sin modificarlo
	uv run ruff format --check .

typecheck: ## Verifica los tipos con ty (Astral)
	uv run ty check

test: ## Ejecuta las pruebas
	uv run pytest

check: lint format-check typecheck test ## VerificaciÃ³n completa (lint + formato + tipos + pruebas)

build: ## Construye el paquete (sdist + wheel)
	uv build

clean: ## Limpia cachÃ©s y artefactos (multiplataforma)
	uv run python -c "import glob,os,shutil; [shutil.rmtree(p,ignore_errors=True) for p in ['.pytest_cache','.ruff_cache','.mypy_cache','dist','build','htmlcov']]; [os.remove(f) for f in ['.coverage'] if os.path.exists(f)]; [shutil.rmtree(p,ignore_errors=True) for p in glob.glob('**/__pycache__',recursive=True)]"
