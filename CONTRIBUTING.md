# Contributing to pazufa-collector-core

Thanks for your interest in the PaZuFa collector core.

## Quick Start

Use [SETUP.md](SETUP.md) for installation. In depth documentation in the [wiki](https://wiki.pazufa.de/books/scraper-core). 

Contributor and maintainer commands live here.

Install Poetry first if it is not already available:
[https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)

```bash
git clone https://codeberg.org/PaZuFa/pazufa-collector-core.git
cd pazufa-collector-core
poetry install --with dev
```

Verify everything passes before opening a PR:

```bash
poetry run ruff check .
poetry run ruff format .
poetry run mypy .
poetry run pytest -v
```

## Tooling

| Tool | Purpose | Run |
|------|---------|---- |
| `ruff check` | Linting | `poetry run ruff check .` |
| `ruff format` | Formatting | `poetry run ruff format .` |
| `mypy` | Static type checking | `poetry run mypy .` |
| `pytest` | Tests | `poetry run pytest -v` |

**mypy** is configured in `pyproject.toml` with strict settings (`disallow_untyped_defs`, `warn_return_any`). All new code must pass type checking. Generated files (`api_model.py`, `api_client/`) are excluded.

To run tests for a specific file or directory:

```bash
poetry run pytest tests/test_specific.py
poetry run pytest tests/test_specific.py::test_function
```

## Language

- **Code, comments, commits, PR descriptions:** English
- **LLM prompts, structured output fields, parliamentary examples:** German where the domain requires it
- German domain terms (Vorgang, Station, Sitzung, Landtag, Ausschuss, etc.) are fine everywhere
- **Wiki:** German

## Git Workflow

1. Create a feature branch from `develop` (or `main` for hotfixes)
2. Make small, focused commits
3. Open a PR for review
4. **Never push directly to `main`**

Branch naming: `feat/short-description`, `fix/short-description`, `chore/short-description`.

Commit style: conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).

### Pull-Requests
For PRs targeting `develop`, the author merges after approval.


## Versioning

After 0.1 is done the first two digits `x.y.z` (`x` and `y`) will be in sync with the version of the Core-lib, because the core lib largely depends on the API. `z` can diverge to avoid unnecessary long version numbers.

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

## Communication

Please update your own status on the [status page in the wiki](https://wiki.pazufa.de/books/scraper-core/page/aktueller-stand) when you start or finish work on a feature or fix.

## Questions?

Open an issue on [Codeberg](https://codeberg.org/PaZuFa/pazufa-collector-core/issues) or reach out to the team.
