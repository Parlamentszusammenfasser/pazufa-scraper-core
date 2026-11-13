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

### Optional extras

OpenTelemetry support is optional. A plain install never imports it.

| Extra       | Installs                                                        | Use it for                                                                                   |
|-------------|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| `otel`      | `opentelemetry-api`                                             | Spans and metrics, if the application sets up its own SDK                                    |
| `otel-otlp` | `opentelemetry-api`, `-sdk`, `-exporter-otlp-proto-http`, `opentelemetry-instrumentation-logging` | `observability.configure()`: readable span log lines and optional OTLP export of traces, metrics and logs |

```bash
poetry add "pazufa_corelib[otel-otlp]~=0.1"
uv add "pazufa_corelib[otel-otlp]~=0.1"
pip install "pazufa_corelib[otel-otlp]~=0.1"
```

The exporter uses OTLP over HTTP/protobuf, so no `grpcio` wheel is needed. See [OpenTelemetry](#opentelemetry-optional) for usage.


### Development

Clone the repository and install it with dev dependencies and all extras (the observability tests need them):

```bash
git clone https://codeberg.org/PaZuFa/pazufa-scraper-core.git
cd pazufa-scraper-core
poetry install --with dev --all-extras
```

`make install` runs the same command.

Or install the latest development branch directly into another project:

**Poetry:**

```bash
poetry add "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@develop"
```

**uv:**

```bash
uv add "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@develop"
```

**pip:**

```bash
pip install "git+https://codeberg.org/PaZuFa/pazufa-scraper-core.git@develop"
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

**Observability** — optional OpenTelemetry helpers (see below):

```python
from pazufa_corelib.observability import span, record_event
from pazufa_corelib.observability import configure  # needs the otel-otlp extra
```

## OpenTelemetry (optional)

`pazufa_corelib.observability` works in two layers:

1. **Instrumentation** (`span()`, `record_event()`, the metric helpers): no extra needed. Without `opentelemetry-api` they do nothing; with the API but no SDK they are no-ops.
2. **Setup** (`configure()`): needs the `otel-otlp` extra. It installs a tracer provider that writes one readable log line per corelib span to the `pazufa_corelib.telemetry` logger (`INFO`, or `WARNING` for failed spans). If an OTLP endpoint is configured, it also exports spans, metrics and log records.

Without the extra, `configure` raises an `ImportError` that names the extra to install.

### Scrapy example

```python
# settings.py
from pazufa_corelib.observability import configure

configure(service_name="pazufa-scraper-bw", instrument_litellm=True)
```

### Logs

With an OTLP endpoint set, `configure()` adds a handler to the root logger that exports every stdlib log record at `log_level` (default `INFO`) and above:

- Fields passed via `extra=` become log attributes. Use the dotted names from `observability._attributes` (e.g. `gen_ai.request.model`, `pazufa.llm.attempt`), so logs, spans and metrics share their keys.
- A record logged inside a span carries that span as native OTLP trace context. Log text and log attributes never contain trace IDs.
- The readable span lines from `pazufa_corelib.telemetry` are not exported: the spans themselves already are.

Call `configure()` after anything that replaces the root handlers (`logging.config.dictConfig` with a `root` section, `basicConfig(force=True)`). A `dictConfig` without a `root` section keeps the existing root handlers.

`configure()` is safe to call twice. If an SDK provider is already set (for example under `opentelemetry-instrument`), it keeps that provider unchanged.

### Environment variables

| Variable                                             | Effect                                                                                             |
|------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT`                        | Enables OTLP/HTTP export (e.g. `http://localhost:4318`). Unset means log lines only                |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`                 | Same, traces only (full URL incl. `/v1/traces`)                                                    |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`                | Same, metrics only (full URL incl. `/v1/metrics`)                                                  |
| `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT`                   | Same, logs only (full URL incl. `/v1/logs`)                                                        |
| `OTEL_EXPORTER_OTLP_HEADERS`                         | Auth headers for the collector, e.g. `authorization=Bearer …`. Keep it in the environment, never in code |
| `OTEL_SERVICE_NAME`                                  | `service.name`, if `configure()` gets no `service_name`                                            |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | With `instrument_litellm=True`: whether prompts and responses are recorded. Default `NO_CONTENT`   |

All other standard `OTEL_*` SDK variables (sampling, timeouts, resource attributes) work as usual.

With `instrument_litellm=True`, litellm calls appear as child spans through the same provider. The corelib registers litellm's V1 integration, so `LITELLM_OTEL_V2` is ignored (a warning is logged).


## CI Workflow

The project uses [Woodpecker CI](https://woodpecker-ci.org/). The pipeline is defined in `.woodpecker.yml` and runs on every push, pull request, and tag.

**On push / pull request** — CI steps run in parallel after setup:

| Step                    | What it does                                                        |
|-------------------------|---------------------------------------------------------------------|
| `setup`                 | Installs Poetry and all dependencies (including dev and all extras) into a `.venv` |
| `check-lock`            | Verifies the `poetry.lock` file is consistent with `pyproject.toml` |
| `format-and-type-check` | Runs `ruff format --check`, `ruff check`, and `mypy`                |
| `audit`                 | Scans dependencies for known vulnerabilities via `pip-audit`        |
| `licenses`              | Checks dependency license compliance via `pylic`                    |
| `test`                  | Runs the test suite via `pytest`                                    |
| `test-without-extras`   | Installs the plain package and checks it imports without OpenTelemetry |

If `audit` fails, follow the [vulnerability response guide](https://wiki.pazufa.de/books/scraper-core/page/vulnerability-response).

**On tag push** — release steps run after all CI steps pass:

| Step                | What it does                                             |
|---------------------|----------------------------------------------------------|
| `build`             | `poetry build` — produces wheel and sdist                |
| `check-dist`        | `twine check` — validates metadata                       |
| `publish-testpypi`  | Uploads to TestPyPI (tags matching `vX.Y.ZrcN`)          |
| `publish-pypi`      | Uploads to PyPI (clean `vX.Y.Z` tags, maintainers only)  |

All steps use `python:3.12-slim`. The virtualenv is created inside the project (`.venv/`) so later steps can use it directly without reinstalling.

## Usage

- For usage documentation see the [wiki](https://wiki.pazufa.de/books/scraper-core).
- For publishing of new Version see [Release Prozess](https://wiki.pazufa.de/link/109#bkmrk-page-title).

## Known Issues

- **Some Poetry commands fail:**
  - Due to the dynamic description of dependencies in the pyproject.toml some Poetry commands like `poetry self show` sometimes do not acknowledge the `poetry.lock` file. This is a known Poetry issue and only cosmetic.
