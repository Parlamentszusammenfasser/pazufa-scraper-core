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

| Tool                | Purpose                               | Make target             |
|---------------------|---------------------------------------|-------------------------|
| `ruff check`        | Linting                               | `make lint`             |
| `ruff format`       | Formatting check                      | `make lint`             |
| `mypy`              | Static type checking                  | `make typecheck`        |
| `pytest`            | Tests                                 | `make test`             |
| `pytest --cov`      | Tests with coverage report            | `make coverage`         |
| `pip-audit`         | Dependency vulnerability scan         | `make security`         |
| `pylic`             | Dependency license compliance check   | `make licenses`         |
| `datamodel-codegen` | Regenerate API models/client          | `make generate`         |
| `detect-secrets`    | Scan for secrets against baseline     | `make secrets-scan`     |
| `detect-secrets`    | Create or update `.secrets.baseline`  | `make secrets-update`   |
| `detect-secrets`    | Interactively audit baseline findings | `make secrets-audit`    |

Run `make` with no target to list all available targets.

**mypy** is configured in `pyproject.toml` with strict settings (`disallow_untyped_defs`, `warn_return_any`). All new code must pass type checking. Generated files (`api_model.py`, `api_client/`) are excluded.

**pylic** enforces dependency license compliance. The allowed license list and any `unsafe_packages` exceptions live under `[tool.pylic]` in `pyproject.toml`. When adding a dependency whose license is not yet in `safe_licenses`, either add the license (if acceptable for the project) or add the package to `unsafe_packages` with a comment explaining why.



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
[codeberg.org/PaZuFa/parlamentszusammenfasser/src/branch/main/openapi.yml](https://codeberg.org/PaZuFa/parlamentszusammenfasser/src/branch/main/openapi.yml),
and released under tags of the form `v<spec>+v<tracks>` (e.g. `v0.2.5+v0.0.7`).

A copy is vendored into this repo as [openapi.yaml](openapi.yaml) — currently
**spec 0.2.5**. Keep it byte-identical to the tag it came from so that
regeneration is reproducible and the diff of a spec bump is readable:

```bash
# note: /api/v1/repos/... and %2B for the "+" in the tag
curl -o openapi.yaml \
  "https://codeberg.org/api/v1/repos/PaZuFa/parlamentszusammenfasser/raw/openapi.yml?ref=v0.2.5%2Bv0.0.7"
make generate-client
```

Use the API route above, not the web `/<owner>/<repo>/raw/...` one: the web
route answers `303 See Other` pointing at `branch/main` and drops the `?ref=`,
so it quietly hands you `main` instead of the tag you asked for. Verify what
you fetched before regenerating:

```bash
grep '^  version:' openapi.yaml   # => version: 0.2.5
```

Do not fix spec problems by editing `openapi.yaml` or the generated client. If
the spec contains something the generator cannot consume, normalise it in
`_patch_spec` (see [Generated Code](#generated-code)) and report it upstream.

The current API version is effectively fixed. Suggestions can be incorporated
for a later API revision, usually with a larger time lag.

## Generated Code

These files are generated and must not be edited by hand — regenerating
silently overwrites any changes:

- [pazufa_corelib/_api_model_generated.py](pazufa_corelib/_api_model_generated.py) from `datamodel-codegen`
- [pazufa_corelib/api_client/](pazufa_corelib/api_client/) from `openapi-python-client`

[pazufa_corelib/api_model.py](pazufa_corelib/api_model.py) is **not** in that
list. It started as generated output but now carries handcrafted additions on
top of `_api_model_generated.py` and
[_api_model_hardening.py](pazufa_corelib/_api_model_hardening.py), so edit it
directly and keep the diff against the generated module readable.

The two generators read from **different sources**, which is easy to trip over:

| Target | Generator | Source |
|---|---|---|
| `_api_model_generated.py` | `datamodel-codegen` | the live endpoint, `tool.datamodel-codegen.url` in [pyproject.toml](pyproject.toml) |
| `api_client/` | `openapi-python-client` | the vendored [openapi.yaml](openapi.yaml) |

So regenerating the Pydantic models can pick up API changes that the client
does not, and vice versa. After a spec bump, regenerate both and check they
agree.

```bash
make generate          # both
make generate-models   # datamodel-codegen only
make generate-client   # openapi-python-client only
```

Relevant generator configuration lives in
[pyproject.toml](pyproject.toml),
[tools/openapi-python-client.yaml](tools/openapi-python-client.yaml) and
[tools/generate_openapi_client.py](tools/generate_openapi_client.py).

### Working around spec problems

`openapi-python-client` rejects some constructs the spec uses, and it does so
by **skipping the affected endpoint** with a warning rather than failing — an
endpoint can disappear from the client without the build going red. Check the
`make generate-client` output for `Endpoint will not be generated`, and diff
the endpoint modules under `pazufa_corelib/api_client/api/` after a bump.

`_patch_spec` in [tools/generate_openapi_client.py](tools/generate_openapi_client.py)
rewrites such constructs on the loaded dict at generation time; `openapi.yaml`
on disk is never modified. It currently strips header `format`s the generator
mis-renders, moves query parameters mislabelled `in: path`, and unwraps
object-typed header schemas.

Keep that hook narrow: it is for declarations that are *invalid* or
unusable as written, not for changes that are merely surprising. Anything that
is valid OpenAPI should be mirrored as-is so the client stays a faithful image
of the tagged spec — pin it with a test instead, and raise it upstream. Every
`_patch_spec` rule needs a test in
[tests/test_generate_openapi_client.py](tests/test_generate_openapi_client.py).

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
