POETRY := poetry run

.PHONY: help check lint typecheck security licenses test coverage format generate generate-models generate-client \
        generate-working-models clean install \
        secrets-scan secrets-update secrets-audit

help:
	@echo "Available targets:"
	@echo "  check          Run all checks (lint, typecheck, poetry, tests)"
	@echo "  lint           Run ruff linter and formatter check"
	@echo "  typecheck      Run mypy"
	@echo "  security       Run pip-audit"
	@echo "  licenses       Run pylic license compliance check"
	@echo "  test           Run pytest"
	@echo "  coverage       Run pytest with coverage report"
	@echo "  format         Auto-fix lint issues and reformat"
	@echo "  generate       Regenerate API models, working models and client"
	@echo "  generate-models Regenerate Pydantic API models with datamodel-codegen"
	@echo "  generate-working-models Regenerate the all-optional mirror of api_model.py"
	@echo "  generate-client Regenerate the OpenAPI client"
	@echo "  clean          Remove build artifacts and caches"
	@echo "  install        Install dev dependencies"
	@echo "  secrets-scan   Scan for secrets using baseline (non-zero exit if new secrets found)"
	@echo "  secrets-update Create or update the .secrets.baseline file"
	@echo "  secrets-audit  Interactively audit the .secrets.baseline file"

check: lint typecheck secrets-scan security licenses
	poetry check
	$(POETRY) pytest -v

lint:
	$(POETRY) ruff check
	$(POETRY) ruff format --check

typecheck:
	$(POETRY) mypy pazufa_corelib

security:
	# Ignored vulnerabilities are tracked as Codeberg issues
	$(POETRY) pip-audit --ignore-vuln CVE-2025-69872

licenses:
	$(POETRY) pylic check

test:
	$(POETRY) pytest -v

coverage:
	$(POETRY) pytest --cov=pazufa_corelib --cov-report=term-missing --cov-report=xml

format:
	$(POETRY) ruff check --fix
	$(POETRY) ruff format

generate: generate-models generate-working-models generate-client

generate-models:
	$(POETRY) datamodel-codegen

# Runs after generate-models only by convention; its source is the handcrafted
# api_model.py, not the spec, so update that first when the API changes.
generate-working-models:
	$(POETRY) python tools/generate_working_models.py

generate-client:
	$(POETRY) python tools/generate_openapi_client.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf dist/ coverage.xml

install:
	poetry install --with dev

secrets-scan:
	$(POETRY) detect-secrets scan --baseline .secrets.baseline

secrets-update:
	$(POETRY) detect-secrets scan --update .secrets.baseline || \
	  $(POETRY) detect-secrets scan > .secrets.baseline

secrets-audit:
	$(POETRY) detect-secrets audit .secrets.baseline