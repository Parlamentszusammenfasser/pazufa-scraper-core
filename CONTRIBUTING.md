# Contributing to pazufa-collector-core

Thanks for your interest in the PaZuFa collector core.

## Quick Start

Use [README.md](README.md) for installation and library usage. Contributor and
maintainer commands live here.

Install Poetry first if it is not already available:
[python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)

```bash
git clone https://codeberg.org/PaZuFa/pazufa-collector-core.git
cd pazufa-collector-core
poetry install --with dev

poetry run black .
poetry run isort .
poetry run mypy .
poetry run pytest
```

## Language

- **Code, comments, commits, PR descriptions:** English
- **LLM prompts, structured output fields, parliamentary examples:** German where the domain requires it
- German domain terms (Vorgang, Station, Sitzung, Landtag, Ausschuss, etc.) are fine everywhere

## Git Workflow

1. Create a feature branch from `develop` (or `main` for hotfixes)
2. Make small, focused commits
3. Open a PR for review
4. **Never push directly to `main`**

Commit style: conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).

## What to Work On

This repository provides shared Python infrastructure for PaZuFa scrapers:

- OpenAPI-based validation models and API client code
- Reusable LLM enrichment prompts, models, and connector logic
- Shared scraper helpers and domain abstractions

Before starting larger work, check existing issues or open one first to avoid duplicate work and to align on scope.

## OpenAPI

The OpenAPI spec is maintained in the main project at
[codeberg.org/PaZuFa/parlamentszusammenfasser/src/branch/main/docs/specs/openapi.yml](https://codeberg.org/PaZuFa/parlamentszusammenfasser/src/branch/main/docs/specs/openapi.yml).

The current API version is effectively fixed. Suggestions can be incorporated
for a later API revision, usually with a larger time lag.

After 0.1 is done the first two digest `x.y.z` (`x` and `y`) will be in sync with version of the Core-lib, because the core lib 
largely depends on the API. `z` can diverge to not have unecessary long version numbers.

## Generated Code

Some files are generated and should usually not be edited by hand:

- [collector_core/api_model.py](collector_core/api_model.py) from `datamodel-codegen`
- [collector_core/api_client/](collector_core/api_client/) from `openapi-python-client`

If you change API-related behavior, prefer updating the OpenAPI source or generator configuration and then regenerate:

```bash
poetry run datamodel-codegen
poetry run python tools/generate_openapi_client.py
```

Relevant generator configuration lives in
[pyproject.toml](pyproject.toml),
[tools/openapi-python-client.yaml](tools/openapi-python-client.yaml) and
[tools/generate_openapi_client.py](tools/generate_openapi_client.py).

## Project Context

This library is one part of the broader [PaZuFa](https://codeberg.org/PaZuFa/parlamentszusammenfasser) system:

- **Backend** (`pazufa-backend`): Rust API serving and validating the data
- **Scrapers / Collectors**: Parliament-specific importers using shared logic from this repo
- **Website** (`pazufa-website`): Frontend presenting the collected data
- **This repo**: Shared Python library for collector integrations, validation, enrichment, and API access

The API and data model are still evolving. If you notice mismatches between this library, the API, and scraper needs, flag them early.

## AI Coding Agents

This project includes an `AGENTS.md` with instructions for AI coding tools (Codex, Claude Code, Cursor, etc.). If you use an AI agent:

- The agent should follow `AGENTS.md` automatically
- Review all generated changes before committing
- Keep PRs small and focused
- Include test evidence for behavior changes
- Pay extra attention to generated code and avoid hand-editing it unless necessary

## Questions?

Open an issue on [Codeberg](https://codeberg.org/PaZuFa/pazufa-collector-core/issues) or reach out to the team.
