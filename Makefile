POETRY := poetry run

.PHONY: help check lint typecheck security test coverage format generate clean install

help:
	@echo "Available targets:"
	@echo "  check      Run all checks (lint, typecheck, poetry, tests)"
	@echo "  lint       Run ruff linter and formatter check"
	@echo "  typecheck  Run mypy"
	@echo "  security   Run pip-audit"
	@echo "  test       Run pytest"
	@echo "  coverage   Run pytest with coverage report"
	@echo "  format     Auto-fix lint issues and reformat"
	@echo "  generate   Regenerate API models and client"
	@echo "  clean      Remove build artifacts and caches"
	@echo "  install    Install dev dependencies"

check: lint typecheck security
	poetry check
	$(POETRY) pytest -v

lint:
	$(POETRY) ruff check
	$(POETRY) ruff format --check

typecheck:
	$(POETRY) mypy pazufa_corelib

security:
	$(POETRY) pip-audit --ignore-vuln GHSA-xqmj-j6mv-4862 \
	                    --ignore-vuln CVE-2025-69872

test:
	$(POETRY) pytest -v

coverage:
	$(POETRY) pytest --cov=pazufa_corelib --cov-report=term-missing --cov-report=xml

format:
	$(POETRY) ruff check --fix
	$(POETRY) ruff format

generate:
	$(POETRY) datamodel-codegen
	$(POETRY) python tools/generate_openapi_client.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf dist/ coverage.xml

install:
	poetry install --with dev