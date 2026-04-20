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
poetry install --with dev
```

Verify everything passes before opening a PR:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy .
poetry run pytest -v
```

## Tooling

| Tool          | Purpose              | Run                        |
|---------------|----------------------|----------------------------|
| `ruff check`  | Linting              | `poetry run ruff check .`  |
| `ruff format` | Formatting           | `poetry run ruff format .` |
| `mypy`        | Static type checking | `poetry run mypy .`        |
| `pytest`      | Tests                | `poetry run pytest -v`     |

**mypy** is configured in `pyproject.toml` with strict settings (`disallow_untyped_defs`, `warn_return_any`). All new code must pass type checking. Generated files (`api_model.py`, `api_client/`) are excluded.



## Documentation

### Repo/Wiki Split

Documentation for this repository is split between the repo itself and the project wiki. The repo contains documentation that is tightly coupled to the code and must remain correct for any given commit: README.md (project overview and orientation), CONTRIBUTING.md (this file), SETUP.md (installation and development environment), and CONFIGURATION.md (configuration keys, environment variables, and config file layout). Changes to these files should accompany the code changes they describe, in the same pull request. All other documentation (f.e. project roadmap, design rationale, glossaries) lives in the project wiki. When wiki content describes current code behavior, please include a note indicating which version or commit it was last verified against.



### Documentation Layout

> Three libraries are aspirational!

Documentation is split between the repository and the project wiki (see the preceding section). Within the repository, documentation is organized around the three published libraries — `corelib`, `scrapy-based`, and `collector-based` — each of which ships to PyPI as an independent package and owns its user-facing documentation.

#### Where to put what

| Content                                                                              | Location                                            |
|--------------------------------------------------------------------------------------|-----------------------------------------------------|
| Project overview, architecture of the three libraries                                | `/README.md`                                        |
| Repo-level contributor setup                                                         | `/SETUP.md`                                         |
| Repo-wide configuration concerns (Dynaconf layering, precedence, `.env` conventions) | `/CONFIGURATION.md`                                 |
| Project license                                                                      | `/LICENSE`                                          |
| Contributing guidelines                                                              | `/CONTRIBUTING.md`                                  |
| Library overview (PyPI front page)                                                   | `<library>/README.md`                               |
| Library license (verbatim copy of `/LICENSE`)                                        | `<library>/LICENSE`                                 |
| Library public configuration schema                                                  | `<library>/CONFIGURATION.md`                        |
| Library release history                                                              | `<library>/CHANGELOG.md`                            |
| Library contributor setup, including optional features                               | `<library>/setup/README.md` and sibling `.md` files |
| Library package definition                                                           | `<library>/pyproject.toml`                          |

`<library>` applies equally to `corelib/`, `scrapy-based/`, and `collector-based/`.

#### Publishing and LICENSE

Each library is published independently to PyPI and has two audiences: external users and repo contributors. Anything that forms part of a library's public contract with external users — `README.md`, `LICENSE`, `CONFIGURATION.md`, `CHANGELOG.md` — lives inside that library's directory so it ships with the packaged distribution. Root-level docs serve the repo; per-library docs serve library users. The two must not duplicate each other; link instead.

Each library's `LICENSE` is a verbatim copy of `/LICENSE` (GPL v3), not a symlink. CI enforces byte-identical content across all four LICENSE files.

Releases follow semantic versioning; changes are recorded in the affected library's `CHANGELOG.md` in the same PR. While a library is pre-1.0, breaking changes are permitted in minor bumps but must still be announced.

#### Setup folders

Each library has a `setup/` folder with `README.md` as its entry point. Additional files cover optional features — e.g. `scrapy-based/setup/ocr.md`. Keep feature setup inline in the folder's `README.md` until it exceeds roughly a screen; then promote it to its own file and link it from the `README.md`. Repo-level `/SETUP.md` stays a flat file at the root.

#### Configuration boundaries

Each library's `CONFIGURATION.md` is the source of truth for that library's own keys. When one library consumes keys defined by another, it links to the upstream schema rather than restating it. Root-level `/CONFIGURATION.md` covers only repo-wide operational concerns (Dynaconf layering, precedence, `.env` conventions) — never library-specific keys.

#### Rules

- Any code change affecting setup, configuration, or public API of a library must update the corresponding docs in the same PR.
- Library `CONFIGURATION.md` files link to upstream schemas rather than restating shared keys.
- Public API changes — including configuration schema and documented extension points — require a `CHANGELOG.md` entry and a semver version bump.
- When any `LICENSE` changes, update all four in the same PR.

### Docstrings

Docstrings are enforced by ruff (pydocstyle rules) using the **Google convention**. All public functions, methods, and classes in `corelib/` require a docstring. Example:

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

poetr### Pull-Requests
For PRs targeting `develop`, the author merges after approval.


## Versioning

After 0.1, the first two version digits (`x.y`) will track the Core-lib version, since the core lib largely depends on the API. `z` can diverge independently to avoid unnecessarily long version numbers.

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

- [corelib/api_model.py](corelib/api_model.py) from `datamodel-codegen`
- [corelib/api_client/](corelib/api_client/) from `openapi-python-client`

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
