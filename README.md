# collector-core

Core library for collectors/scrapers of [PaZuFa](https://codeberg.org/PaZuFa/parlamentszusammenfasser.git), providing shared functionality and base classes.

## Structure
The core lib consists of three parts:
1. **General Library**  Shared classes and utilities used by all scrapers regardless of implementation approach. This includes [Pydantic](https://docs.pydantic.dev/latest/) validation models, API client helpers, common data transformation functions, standardised phrases and tag mappings (e.g. normalising committee names, document types, and Schlagworte across parliaments), and reusable components for tasks like LLM enrichment.
2. **[Scrapy](https://www.scrapy.org/)-based** Implementation Template — An opinionated scaffolding for scrapers built on Scrapy. Provides pre-configured pipelines, middleware, and base spider classes that integrate with the general library.
3. **Standalone Collector Template** — An opinionated scaffolding for scrapers that don't use Scrapy, implementing their own HTTP fetching and scheduling logic while relying on the general library for validation, API submission, and enrichment.



## Requirements

- Python 3.12+

## Installation

Install using Poetry:

```bash
poetry add collector-core
# or
poetry add git+https://github.com/Parlamentszusammenfasser/collector-core.git
```

Or with pip:

```bash
pip install collector-core
# or for local dev
pip install -e .
```

## Usage

```python
import collector_core
```

## Development

This project uses Poetry for dependency management.

### Setup

```bash
# Install dependencies
poetry install --with dev

# Run formatting and tests
poetry run isort .
poetry run black .
poetry run pytest

# to update API model
poetry run datamodel-codegen

# to update API client
poetry run python3 tools/generate_openapi_client.py
```

## License

TBD
