# Setup

This document describes the setup of the repo itself and some common setup tasks between all three sub repos (not
implemented yet).

For more detail, look at the setup files in the sub repos (not implemented yet).

## Requirements

- Python 3.12+
- Poetry 2.x

For the full dependency list, see [pyproject.toml](pyproject.toml).

## Installation

### Stable

Once published, install using Poetry (advised), uv, or pip.

It is strongly advised to pin the version below the next minor (`x.Y`) release, as minor bumps indicate major reworks
that will most likely be breaking.

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

The package is installed and imported as `pazufa_corelib`. (PEP 503 normalization means `pip install pazufa-corelib` is
also accepted.)

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

## Observability

**Decision (#164): the corelib stays out of observability.** It is a library, not an application, so it neither
integrates OpenTelemetry nor depends on any metrics, logging or tracing stack. The scraper that uses it chooses and sets
up its own (Loki, Prometheus, OTel, …). The corelib only hands over what it knows: plain log records and the numbers
below, which the scraper pushes wherever it likes.

- **Logs:** every module logs to `logging.getLogger(__name__)` (`pazufa_corelib.*`). Records reach whatever handlers the
  scraper puts on the root logger.
- **LLM usage:** `LLMConnector.prompt_tokens`, `completion_tokens`, `reasoning_tokens` (part of completion) and
  `cost_usd` add up over every provider response of one connector, including validation retries and failed
  extractions. `cost_usd` is the cost the provider reports (OpenRouter does). It stays `None` until a provider reports a
  cost, so "not reported" can't be mistaken for "free". Calls that fail without a response (timeouts, connection errors)
  count neither tokens nor cost.
- **Normalization:** the resolution objects carry `score`, `matched` and `changed`, so a scraper can count outcomes
  itself.

**Tracing needs no corelib code.** OpenTelemetry carries the trace context in `contextvars`, not in function
arguments. Setting up the OTel SDK alone is not enough, though: the `traceparent` header is added by the httpx
instrumentation, which the scraper has to enable once, after setting up its tracer provider. Because the API client uses
httpx, its requests to the backend then become child spans of the scraper's current span and carry the header.
The litellm callback does the same for LLM calls:

```python
import os

import litellm
from litellm.integrations.opentelemetry import OpenTelemetry, OpenTelemetryConfig
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

HTTPXClientInstrumentor().instrument()  # API client: client spans and traceparent header
# Without it, litellm writes onto the parent span, which has ended when its callback runs.
os.environ.setdefault("USE_OTEL_LITELLM_REQUEST_SPAN", "true")
# An instance, not the string "otel", so litellm reuses the global tracer provider.
# NO_CONTENT: otherwise litellm records prompts and responses.
litellm.callbacks.append(
    OpenTelemetry(config=OpenTelemetryConfig(capture_message_content="NO_CONTENT"))
)
```

For this to keep working, the API client stays open to instrumentation (`httpx_args`, `set_async_httpx_client`,
`with_headers`) and LLM calls keep going through litellm.

## CI Workflow

The project uses [Woodpecker CI](https://woodpecker-ci.org/). The pipeline is defined in `.woodpecker.yml` and runs on
pull requests, pushes to `main`, tags, and manual runs.

**Always** — CI steps run in parallel after setup:

| Step                    | What it does                                                        |
|-------------------------|---------------------------------------------------------------------|
| `setup`                 | Installs Poetry and all dependencies (including dev) into a `.venv` |
| `check-lock`            | Verifies the `poetry.lock` file is consistent with `pyproject.toml` |
| `format-and-type-check` | Runs `ruff format --check`, `ruff check`, and `mypy`                |
| `audit`                 | Scans dependencies for known vulnerabilities via `pip-audit`        |
| `licenses`              | Checks dependency license compliance via `pylic`                    |
| `test`                  | Runs the test suite via `pytest`                                    |

If `audit` fails, follow
the [vulnerability response guide](https://wiki.pazufa.de/books/scraper-core/page/vulnerability-response).

**On manual run** — after all CI steps pass, `release` bumps the version, commits, tags and pushes to `main` (see
[Releasing](CONTRIBUTING.md#releasing)). Runs on other branches fail.

**On tag push** — publish steps run after all CI steps pass:

| Step               | What it does                                            |
|--------------------|---------------------------------------------------------|
| `check-version`    | Tag matches the version in `pyproject.toml`             |
| `check-on-main`    | Final `vX.Y.Z` tags must point at a commit on `main`    |
| `check-not-published` | The version is not on (Test)PyPI yet                 |
| `build`            | `poetry build` — produces wheel and sdist               |
| `check-dist`       | `twine check` — validates metadata                      |
| `publish-testpypi` | Uploads to TestPyPI (tags matching `vX.Y.ZrcN`)         |
| `publish-pypi`     | Uploads to PyPI (clean `vX.Y.Z` tags, maintainers only) |

All steps use `python:3.12-slim`. The virtualenv is created inside the project (`.venv/`) so later steps can use it
directly without reinstalling.

## Usage

- For usage documentation see the [wiki](https://wiki.pazufa.de/books/scraper-core).
- For publishing of new Version see [Release Prozess](https://wiki.pazufa.de/link/109#bkmrk-page-title).

## Known Issues

- **Some Poetry commands fail:**
    - Due to the dynamic description of dependencies in the pyproject.toml some Poetry commands like `poetry self show`
      sometimes do not acknowledge the `poetry.lock` file. This is a known Poetry issue and only cosmetic.
