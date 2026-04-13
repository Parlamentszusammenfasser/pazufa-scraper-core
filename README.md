# Scraper-core

Core library for collectors/scrapers of [PaZuFa](https://codeberg.org/PaZuFa/parlamentszusammenfasser.git), providing shared functionality and base classes.

> **Status:** Work in Progress (WIP). For a detailed status overview see the [status page in the wiki](https://wiki.pazufa.de/books/scraper-core/page/aktueller-stand) (German).



A detailed documentation can be found in the [wiki](https://wiki.pazufa.de/books/scraper-core) (German).



## Requests

If you have a request for the Scraper-core the best way to voice it is to write a Codeberg issue. Please add the label `external-request` to it.

If it is a bug you can alternatively use the lable `Bug`.

For requests and questions, you can, of course contact us on Mattermost.

## Structure

The library consists of three parts:

1. **CoreLib** — Shared classes and utilities used by all scrapers regardless of implementation approach. This includes [Pydantic](https://docs.pydantic.dev/latest/) validation models, API client helpers, common data transformation functions, standardised phrases and tag mappings (e.g. normalising committee names, document types, and Schlagworte across parliaments), and reusable components for tasks like LLM enrichment.
2. **[Scrapy](https://www.scrapy.org/)-based Implementation Template** — An opinionated scaffolding for scrapers built on Scrapy. Provides pre-configured pipelines, middleware, and base spider classes that integrate with the general library.
3. **Standalone Collector Template** — An opinionated scaffolding for scrapers that don't use Scrapy, implementing their own HTTP fetching and scheduling logic while relying on the general library for validation, API submission, and enrichment.

## Requirements

- Python 3.12+
- Poetry 2.x

 For the full dependency list see [pyproject.toml](pyproject.toml). 

## Setup 

The package is not yet published to PyPI. Install directly from the repository:

**Poetry:**

```bash
poetry add git+https://codeberg.org/PaZuFa/pazufa-collector-core.git
```

**pip:**

```bash
pip install git+https://codeberg.org/PaZuFa/pazufa-collector-core.git
```

To pin a specific version, append `@<tag>` or `@<commit>`:

```bash
poetry add git+https://codeberg.org/PaZuFa/pazufa-collector-core.git@v0.1.0
pip install git+https://codeberg.org/PaZuFa/pazufa-collector-core.git@v0.1.0
```

See [SETUP.md](SETUP.md) for the full setup guide, which is versioned alongside the code.

## Contribution

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, git workflow, code generation, documentation and project context.

## License

GPL-3.0
