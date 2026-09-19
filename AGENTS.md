# AGENTS.md — pazufa-scraper-core

Cross-tool instructions for AI coding agents working on this project.

## Core Principles

**This library is shared by multiple collectors and scrapers.** Changes here have a wider blast radius than application-local code.

### Maintainability

- Prefer simple, readable Python over clever abstractions
- Keep public APIs stable unless a breaking change is explicitly intended
- Minimize dependencies and justify every new package
- Solve current use cases directly; do not build speculative framework layers
- When changing shared behavior, consider impact on downstream scrapers and generated clients

If a design choice improves short-term convenience but increases long-term maintenance cost, flag it.

### Security

- Never trust external input; validate at boundaries
- No secrets in code, fixtures, or documentation
- Mock provider/network calls in tests unless a task explicitly requires live integration
- Treat API keys and model credentials as environment configuration only

### Logging

- Log errors, retries, provider failures, and unexpected states
- Avoid noisy logs in hot paths
- Prefer structured, actionable log messages over generic text

## Build & Verify

Before finishing work, run all checks:

```bash
make check
```

This runs linting, type checking, security audit, and the full test suite. Other targets:

| Target           | What it does                              |
|------------------|-------------------------------------------|
| `make lint`      | `ruff check` + `ruff format --check`      |
| `make typecheck` | `mypy pazufa_corelib`                     |
| `make security`  | `pip-audit`                               |
| `make test`      | `pytest -v`                               |
| `make coverage`  | pytest with term + XML coverage report    |
| `make format`    | auto-fix lint and reformat                |
| `make generate`  | regenerate API models and client          |
| `make clean`     | remove caches, `dist/`, `coverage.xml`    |

To regenerate API models and client after OpenAPI changes:

```bash
make generate
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for further detail on tooling and code generation.

## CI Pipeline

The project uses [Woodpecker CI](https://woodpecker-ci.org/). The pipeline runs on every push and pull request:

| Step | What it does |
|------|--------------|
| `setup` | Installs Poetry and all dependencies (including dev) into `.venv` |
| `check-lock` | Verifies `poetry.lock` is consistent with `pyproject.toml` |
| `format-and-type-check` | Runs `ruff format --check`, `ruff check`, and `mypy` |
| `test` | Runs the test suite via `pytest` |

The last three steps run in parallel after `setup`. All steps use `python:3.12-slim`.

## Tech Stack

- **Python 3.12**
- **Poetry** for dependency management
- **Pydantic v2** for validation and structured models
- **pytest**, **pytest-asyncio**, **pytest-cov** for testing
- **ruff** for linting (`ruff check`) and formatting (`ruff format`)
- **mypy** for static type checking (strict: `disallow_untyped_defs`, `warn_return_any`)
- **LiteLLM** + **Instructor** for provider-agnostic LLM integration
- **Woodpecker CI** verifies formatting, type checks, and tests

## Code Style

- Use Python 3.12 features deliberately, but keep code straightforward
- Public functions, methods, and classes should be typed
- Preserve compatibility with the configured `mypy` strictness
- Prefer explicit domain exceptions over generic `Exception` or `RuntimeError`

### Language

| Context | Language |
|---------|----------|
| Code, comments, commits, PR descriptions | English |
| LLM prompts, structured output fields, parliamentary examples | German where the domain requires it |
| Wiki | German |

German domain terms (Vorgang, Station, Sitzung, TOP, Sachgebiet, Landtag, Ausschuss, etc.) are fine in identifiers when they improve clarity.

### Docstrings

Docstrings follow the **Google convention** and are enforced by ruff (pydocstyle rules). All public functions, methods, and classes in `pazufa_corelib/` require a docstring:

```python
def my_function(arg: str) -> int:
    """Short one-line summary.

    Args:
        arg: Description of the argument.

    Returns:
        Description of the return value.
    """
```

Exceptions — no docstring required for:
- `__init__` methods (document the class instead)
- Public modules and packages
- `tests/`, `tools/`, and generated files (`api_client/`, `api_model.py`)

## Normalization Module Notes

### Name resolution

`AuthorResolver` and `OrganizationResolver` both normalize via `normalize_name` (honorific stripping + umlaut fold + token sort) before matching. Both support:

- **Exact lookup** (normalized key index) before falling back to fuzzy/cosine matching
- **Constructor params**: `AuthorResolver(files=[…], match_threshold=…)`, `OrganizationResolver(files=[…], match_threshold=…, near_tie_epsilon=…)`
- Use `OrganizationResolver.explain(query, k=5)` to trace resolution candidates for debugging

### Organization file structure

`Organization.acronym` is a required field (never has a default). Every entry in an org YAML must declare it — use `acronym:` (bare key) for entries without an abbreviation. `Author` rejects extra fields (`extra="forbid"`). Together these make loading the wrong file type a hard `ValidationError` rather than a silent no-op.

Party entries in `parteien.yaml` use the short acronym as `canonical_name` (e.g. `CDU`, `SPD`). CDU, CSU, and the CDU/CSU Fraktion are three distinct entries (`cdu`, `csu`, `cdu-csu`).

### Experimental functions

Functions marked experimental emit a `DeprecationWarning` and may be removed without notice. When calling them in tests, use `pytest.warns(DeprecationWarning)`. Example: `normalize_autor`.

### YAML validator tools

Candidate vocabulary YAML files can be checked for ID, exact-name, and fuzzy collisions before merging. Each validator lives in its own module under `tools/` and can be invoked two ways:

**As a CLI** (positional `files` replace the built-in defaults; warnings are printed, hard errors exit 1):

```bash
poetry run python -m tools.yaml_validator_authors my_authors.yaml
poetry run python -m tools.yaml_validator_organizations my_orgs.yaml
poetry run python -m tools.yaml_validator_tags my_tags.yaml
```

**As Python functions** — import directly from the validator's own module (not `from tools import …`, since `tools/__init__.py` is intentionally docstring-only to avoid the `python -m` double-load warning):

```python
from pathlib import Path

from tools.yaml_validator_authors import yaml_validator_authors
from tools.yaml_validator_organizations import yaml_validator_organizations
from tools.yaml_validator_tags import yaml_validator_tags

yaml_validator_authors(Path("my_authors.yaml"))
yaml_validator_organizations(
    Path("my_orgs.yaml"),
    files=[Path("already_merged.yaml")],  # replaces built-in ORGANIZATIONS_FILES
)
yaml_validator_tags(Path("my_tags.yaml"), match_threshold=85)
```

Each function raises `ValueError` on collisions / schema problems and `FileNotFoundError` if the candidate path is missing; warnings go to stdout. See `SETUP_NORMALIZATION.md` ("Validating New Files Before Merging") for the full check matrix and threshold defaults.

## Testing Expectations

- Add or update tests for every behavior change
- Keep external I/O mocked in unit tests
- Use `@pytest.mark.asyncio` for async behavior
- Cover retry, validation, and failure paths when changing connector logic
- If you change generated API models or clients, verify regeneration and affected tests together
- To cover `if LOGGER.isEnabledFor(logging.DEBUG):` branches, use `caplog.at_level(logging.DEBUG, logger="pazufa_corelib.normalization.names")` in the test

Run a specific test file or function:

```bash
poetry run pytest tests/test_specific.py
poetry run pytest tests/test_specific.py::test_function
```

## Git Workflow

- Branch from `develop` for features and fixes; branch from `main` for hotfixes only
- **Never push directly to `main`**
- Open a PR for review; for PRs targeting `develop`, the author merges after approval
- Keep commits small and focused

**Branch naming:** `feat/short-description`, `fix/short-description`, `chore/short-description`

**Commit style:** conventional commits — `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`

## Generated Code

These paths are generated and should not be hand-edited unless the task explicitly requires it:

- [pazufa_corelib/_api_model_generated.py](pazufa_corelib/_api_model_generated.py)
- [pazufa_corelib/api_model_working.py](pazufa_corelib/api_model_working.py)
- [pazufa_corelib/api_client/](pazufa_corelib/api_client/)

[pazufa_corelib/api_model.py](pazufa_corelib/api_model.py) is handcrafted and is
the input for `api_model_working.py` — edit it directly.

Prefer changing one of these inputs instead:

- [pyproject.toml](pyproject.toml) - `tool.datamodel-codegen`
- [tools/generate_working_models.py](tools/generate_working_models.py)
- [tools/openapi-python-client.yaml](tools/openapi-python-client.yaml)
- [tools/generate_openapi_client.py](tools/generate_openapi_client.py)
- See [CONTRIBUTING.md](CONTRIBUTING.md#openapi) for OpenAPI source-of-truth notes

Then regenerate and review the diff carefully.

## Project Structure

- `pazufa_corelib/__init__.py` - public package exports
- `pazufa_corelib/llm/` - LLM connector, models, and prompts
- `pazufa_corelib/normalization/` - text, date, URL, hash, name, and Schlagworte helpers
  - `names.py` - `normalize_name`, `AuthorResolver`, `OrganizationResolver`; experimental `normalize_autor`
  - `text.py` - `normalize_name_key`, `normalize_volltext`
  - `date.py` - `normalize_datum`
  - `hash.py` - content hashing utilities
  - `urls.py` - URL normalization
  - `schlagworte.py` - controlled topic taxonomy helpers
  - `_fuzzy.py` - shared fuzzy-match internals
- `pazufa_corelib/names_model.py` - `Author`, `Organization`, `AuthorIDResolution`, `OrganizationIDResolution`
- `pazufa_corelib/api_model.py` - generated Pydantic models
- `pazufa_corelib/api_client/` - generated OpenAPI client
- `tests/` - unit tests
- `tools/` - code generation helpers

## Key Domain Concepts

- **Vorgang** = legislative proceeding across its full lifecycle
- **Station** = one step within a Vorgang
- **Sitzung** = parliamentary or committee session
- **TOP** = agenda item (`Tagesordnungspunkt`)
- **Sachgebiet** = controlled topic taxonomy used for enrichment and classification

## Related Repos

- Main project repo: [codeberg.org/PaZuFa/parlamentszusammenfasser](https://codeberg.org/PaZuFa/parlamentszusammenfasser)
- Website: [codeberg.org/PaZuFa/pazufa-website](https://codeberg.org/PaZuFa/pazufa-website)
- Shared library: [codeberg.org/PaZuFa/pazufa-scraper-core](https://codeberg.org/PaZuFa/pazufa-scraper-core)