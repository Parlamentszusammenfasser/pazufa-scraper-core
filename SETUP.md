# Setup

This document describes the setup of the repo itself and some common setup tasks between all three sub repos (not implemented yet).

For more detail, look at the setup files in the sub repos (not implemented yet).

## Requirements

- Python 3.12+
- Poetry 2.x

 For the full dependency list, see [pyproject.toml](pyproject.toml). 

## Installation

### Stable

Once published, install using Poetry (advised), uv, or pip.

It is strongly advised to pin the version below the next minor (`x.Y`) release, as minor bumps indicate major reworks that will most likely be breaking.

The examples below prescribe a version `0.1` and above, but under `0.2`.

**Poetry:**

```bash
poetry add "pazufa_corelib~=0.1"
```

**uv:**

```bash
uv add "pazufa_corelib~=0.1"
```

**pip:**

```bash
pip install "pazufa_corelib~=0.1"
```


### Development

Clone the repository and install it with dev dependencies:

```bash
git clone https://codeberg.org/PaZuFa/pazufa-scraper-core.git
cd pazufa-scraper-core
poetry install --with dev
```

Or install the latest unreleased state of `main` directly into another project:

**Poetry:**

```bash
poetry add "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@main"
```

**uv:**

```bash
uv add "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@main"
```

**pip:**

```bash
pip install "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@main"
```
## Importing pazufa_corelib

The package is installed and imported as `pazufa_corelib`. (PEP 503 normalization means `pip install pazufa-corelib` is also accepted.)

**API client** — authenticated HTTP client for the LTZF API:

```python
from pazufa_corelib.api_client import AuthenticatedClient, Client
```

**Normalization** — text, date, URL, and hash helpers:

```python
from pazufa_corelib.normalization import normalize_datum, normalize_volltext, normalize_url
from pazufa_corelib.normalization import hash_text, hash_bytes
```

**LLM enrichment** — connector, Pydantic result models, and prompt templates:

```python
from pazufa_corelib.llm import LLMConnector
from pazufa_corelib.llm import ZusammenfassungResult, SchlagworteResult
from pazufa_corelib.llm import ZUSAMMENFASSUNG_PROMPT, SCHLAGWORTE_PROMPT
```


## CI Workflow

The project uses [Woodpecker CI](https://woodpecker-ci.org/). The pipeline consists of three workflows in `.woodpecker/`.

**`checks.yml`** — on every push, pull request and tag:

| Step                    | What it does                                                        |
|-------------------------|---------------------------------------------------------------------|
| `lint-pipeline`         | `woodpecker-cli lint` on the workflow files                         |
| `setup`                 | Installs Poetry and all dependencies (including dev) into a `.venv`, wheels only |
| `check-lock`            | Verifies the `poetry.lock` file is consistent with `pyproject.toml` |
| `audit`                 | Scans dependencies for known vulnerabilities via `pip-audit`; the steps below wait for it |
| `secrets`               | `detect-secrets-hook` against `.secrets.baseline`                   |
| `format-and-type-check` | Runs `ruff format --check`, `ruff check`, and `mypy`                |
| `licenses`              | Checks dependency license compliance via `pylic`                    |
| `build`                 | `poetry build`, `twine check`, and an import of the installed wheel |

If `audit` fails, follow the [vulnerability response guide](https://wiki.pazufa.de/books/scraper-core/page/vulnerability-response).
If `secrets` reports a false positive, mark it with `# pragma: allowlist secret` or run `make secrets-update` and audit the baseline.

**`test.yml`** — after `checks`: `pytest` (with the 85 % coverage gate) on Python 3.12, 3.13 and 3.14.

**`release.yml`** — on tag push, after `checks` and `test` pass:

| Step                  | What it does                                                 |
|-----------------------|--------------------------------------------------------------|
| `check-version`       | Tag matches the version in `pyproject.toml`                  |
| `check-on-main`       | Final `vX.Y.Z` tags must point at a commit on `main`         |
| `check-not-published` | The version is not on (Test)PyPI yet                         |
| `build`               | `poetry build` and `twine check`                             |
| `publish-testpypi`    | Uploads to TestPyPI (tags matching `vX.Y.ZrcN`)              |
| `publish-pypi`        | Uploads to PyPI (clean `vX.Y.Z` tags, maintainers only)      |

Images are pinned by digest and Poetry by exact version; update them by hand in all three files. The `pypi_token` and `testpypi_token` secrets must be limited to the `tag` event in the repository settings.

## Usage

- For usage documentation see the [wiki](https://wiki.pazufa.de/books/scraper-core).
- For publishing of new Version see [Release Prozess](https://wiki.pazufa.de/link/109#bkmrk-page-title).

## Known Issues

- **Some Poetry commands fail:**
  - Due to the dynamic description of dependencies in the pyproject.toml some Poetry commands like `poetry self show` sometimes do not acknowledge the `poetry.lock` file. This is a known Poetry issue and only cosmetic.
