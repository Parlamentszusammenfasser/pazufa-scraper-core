# AGENTS.md — pazufa-collector-core

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
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy .
poetry run pytest -v
```

To regenerate API models and client after OpenAPI changes:

```bash
poetry run datamodel-codegen
poetry run python tools/generate_openapi_client.py
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

Docstrings follow the **Google convention** and are enforced by ruff (pydocstyle rules). All public functions, methods, and classes in `collector_core/` require a docstring:

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

## Testing Expectations

- Add or update tests for every behavior change
- Keep external I/O mocked in unit tests
- Use `@pytest.mark.asyncio` for async behavior
- Cover retry, validation, and failure paths when changing connector logic
- If you change generated API models or clients, verify regeneration and affected tests together

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

- [collector_core/api_model.py](collector_core/api_model.py)
- [collector_core/api_client/](collector_core/api_client/)

Prefer changing one of these inputs instead:

- [pyproject.toml](pyproject.toml) - `tool.datamodel-codegen`
- [tools/openapi-python-client.yaml](tools/openapi-python-client.yaml)
- [tools/generate_openapi_client.py](tools/generate_openapi_client.py)
- See [CONTRIBUTING.md](CONTRIBUTING.md#openapi) for OpenAPI source-of-truth notes

Then regenerate and review the diff carefully.

## Project Structure

- `collector_core/__init__.py` - public package exports
- `collector_core/llm_connector.py` - current LLM entrypoint; LLM-related code is expected to move into `collector_core/llm/`
- `collector_core/api_model.py` - generated Pydantic models
- `collector_core/api_client/` - generated OpenAPI client
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
- Shared library: [codeberg.org/PaZuFa/pazufa-collector-core](https://codeberg.org/PaZuFa/pazufa-collector-core)