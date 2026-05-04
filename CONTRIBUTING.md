# Contributing to pazufa-scraper-core

Thanks for your interest in the PaZuFa scraper core.

## Quick Start

Use [SETUP.md](SETUP.md) for installation. Place in depth documentation in the [wiki](https://wiki.pazufa.de/books/scraper-core). 

Contributor and maintainer commands live here.

Install Poetry first if it is not already available:
[https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)

```bash
git clone https://codeberg.org/PaZuFa/pazufa-scraper-core.git
cd pazufa-scraper-core
make install
```

Verify everything passes before opening a PR:

```bash
make check
```

## Tooling

| Tool                | Purpose                       | Make target      |
|---------------------|-------------------------------|------------------|
| `ruff check`        | Linting                       | `make lint`      |
| `ruff format`       | Formatting check              | `make lint`      |
| `mypy`              | Static type checking          | `make typecheck` |
| `pytest`            | Tests                         | `make test`      |
| `pytest --cov`      | Tests with coverage report    | `make coverage`  |
| `pip-audit`         | Dependency vulnerability scan | `make security`  |
| `datamodel-codegen` | Regenerate API models/client  | `make generate`  |

Run `make` with no target to list all available targets.

**mypy** is configured in `pyproject.toml` with strict settings (`disallow_untyped_defs`, `warn_return_any`). All new code must pass type checking. Generated files (`api_model.py`, `api_client/`) are excluded.



## Documentation

### Repo/Wiki Split

Documentation for this repository is split between the repo itself and the project wiki. The repo contains documentation that is tightly coupled to the code and must remain correct for any given commit: README.md (project overview and orientation), CONTRIBUTING.md (this file), SETUP.md (installation and development environment), and CHANGELOG.md (notable changes per release). Changes to these files should accompany the code changes they describe, in the same pull request. All other documentation (e.g., project roadmap, design rationale, glossaries) lives in the project wiki. When wiki content describes current code behavior, please include a note indicating which version or commit it was last verified against.

### Docstrings

Docstrings are enforced by ruff (pydocstyle rules) using the **Google convention**. All public functions, methods, and classes in `pazufa_corelib/` require a docstring. Example:

```python
def my_function(arg: str) -> int:
    """Short one-line summary.

    Args:
        arg: Description of the argument.

    Returns:
        Description of the return value.
    """
```

Exceptions:
- `__init__` methods (D107 — document the class instead)
- Public modules and packages (D100, D104)
- `tests/`, `tools/`, and generated files (`api_client/`, `api_model.py`) are fully excluded

To run tests for a specific file or directory:

```bash
poetry run pytest tests/test_specific.py
poetry run pytest tests/test_specific.py::test_function
```

## Language

- **Code, comments, commits, PR descriptions:** English, American English is preferred but not enforced.
- **LLM prompts, structured output fields, parliamentary examples:** German where the domain requires it
- German domain terms (Vorgang, Station, Sitzung, Landtag, Ausschuss, etc.) are fine everywhere
- **Wiki:** German
- A glossary for this project can be found in the [relevant Wiki page](https://wiki.pazufa.de/books/scraper-core/page/scraper-core-glossar).

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

After 0.1, the first two version digits (`x.y`) will track the Core-lib version, since the core lib largely depends on the API. `z` can diverge independently to avoid unnecessarily long version numbers.

## What to Work On

For what to work on, please look at the issues in this repo. A longer term view can be found in the [Roadmap](https://wiki.pazufa.de/books/scraper-core/page/roadmap) for this project. 

## OpenAPI

The OpenAPI spec is maintained in the main project at
[codeberg.org/PaZuFa/parlamentszusammenfasser/src/branch/main/docs/specs/openapi.yml](https://codeberg.org/PaZuFa/parlamentszusammenfasser/src/branch/main/docs/specs/openapi.yml).

The current API version is effectively fixed. Suggestions can be incorporated
for a later API revision, usually with a larger time lag.

## Generated Code

Some files are generated and should usually not be edited by hand:

- [pazufa_corelib/api_model.py](pazufa_corelib/api_model.py) from `datamodel-codegen`
- [pazufa_corelib/api_client/](pazufa_corelib/api_client/) from `openapi-python-client`

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

Open an issue on [Codeberg](https://codeberg.org/PaZuFa/pazufa-scraper-core/issues) or reach out to the team.
