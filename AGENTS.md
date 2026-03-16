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

Use [CONTRIBUTING.md](CONTRIBUTING.md) as the source of truth for local setup,
verification, and code generation commands. Before finishing work, run the
relevant checks from there.

## Tech Stack

- **Python 3.12**
- **Poetry** for dependency management
- **Pydantic v2** for validation and structured models
- **pytest**, **pytest-asyncio**, **pytest-cov** for testing
- **mypy**, **black**, **isort** for static checks and formatting
- **LiteLLM** + **Instructor** for provider-agnostic LLM integration
- **Woodpecker CI** verifies formatting, type checks, and tests

## Code Style

- Use Python 3.12 features deliberately, but keep code straightforward
- Public functions, methods, and classes should be typed
- Preserve compatibility with the configured `mypy` strictness
- Code, comments, and docstrings: **English**
- Prompts, examples, and output schemas may be **German** where required by the parliamentary domain
- German domain terms (Vorgang, Station, Sitzung, TOP, Sachgebiet, etc.) are fine in identifiers when they improve clarity
- Add docstrings for public APIs and non-obvious logic
- Prefer explicit domain exceptions over generic `Exception` or `RuntimeError`

## Testing Expectations

- Add or update tests for every behavior change
- Keep external I/O mocked in unit tests
- Use `@pytest.mark.asyncio` for async behavior
- Cover retry, validation, and failure paths when changing connector logic
- If you change generated API models or clients, verify regeneration and affected tests together

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

- [collector_core/__init__.py](collector_core/__init__.py) - public package exports
- [collector_core/llm_connector.py](collector_core/llm_connector.py) - current LLM entrypoint; LLM-related code is expected to move into `collector_core/llm/`
- [collector_core/api_model.py](collector_core/api_model.py) - generated Pydantic models
- [collector_core/api_client/](collector_core/api_client/) - generated OpenAPI client
- [tests/](tests/) - unit tests
- [docs/](docs/) - module-level documentation
- [tools/](tools/) - code generation helpers

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
