# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- **`AuthorResolver`** (`pazufa_corelib/normalization/names.py`) — fuzzy author-name resolver backed by a YAML vocabulary. Supports `resolve()`, `resolve_batch()`, `get_author_by_id()`, `check_author()`, `fuzzy_check_author()`, and `explain()` for diagnostics. Configurable `match_threshold`; aliases and umlaut folding handled automatically.
- **`OrganizationResolver`** — cosine-similarity resolver for organization names, with configurable `match_threshold` and `near_tie_epsilon`. Exposes `resolve()`, `resolve_batch()`, `get_organization_by_id()`, `check_organization()`, and `explain()`.
- **`names_model`** (`pazufa_corelib/names_model.py`) — Pydantic models `Author`, `Organization`, `AuthorFile`, `AuthorIDResolution`, and `NameIDResolution` for the author/organization normalization chain.
- **Global YAML vocabularies** under `pazufa_corelib/normalization/mappings/`: `authors.yaml`, `organizations.yaml`, and `parteien.yaml` (political parties).
- **`normalize_autor`** — experimental high-level function that combines `AuthorResolver` and `OrganizationResolver` to resolve a raw author string to a canonical name and ID.
- **YAML validator tools** (`tools/`) — three CLI scripts for pre-merge conflict detection:
  - `yaml_validator_authors.py` — checks ID collisions, exact `canonical_name` collisions, and fuzzy near-matches against the global author vocabulary.
  - `yaml_validator_organizations.py` — same checks for organizations using cosine similarity.
  - `yaml_validator_tags.py` — checks tag ID collisions and fuzzy ID near-matches against the global tag vocabulary.
  - All tools accept positional `extra_files` for unreleased context files and support `--match-threshold` / `--near-tie-epsilon` flags.
- **`SETUP_NORMALIZATION.md`** — step-by-step guide for extending the author, organization, and tag/Sachgebiet vocabularies, including YAML format reference, usage examples, and validator instructions.
- **`Makefile`** — common development commands (`make check`, `make test`, `make lint`, etc.).

### Changed
- **`SchlagwortResolver` — configurable thresholds** — `__init__` now accepts `match_threshold` (default 90) and `near_tie_epsilon` (default 1.0), forwarded to all internal fuzzy operations and reflected in `explain()` traces.
- **`_canonicalise_ids` — configurable `near_tie_epsilon`** — the private helper now accepts a `near_tie_epsilon` parameter (default `_NEAR_TIE_EPSILON`) instead of always using the module constant.
- **Supported Pythonversions** — dropped support for Python 3.14, as the new liteLLM Versions do not support it.

### Experimental
- **'normalize_autor'** — Normalize the ``organisation`` and ``person`` fields of an Autor in-place. Resolves each field against the provided resolvers and updates it to the
    canonical name if a match is found; logs debug information otherwise. (Experimental, due to open decion if such a function should be part of the Corelib or only of the -based Implementations [planned for v0.2])


### Fixed

- Bug fixes in author normalization logic and associated tests.
- Bug fix, python-dateutil now explicitly named as an dependency.
- Multiple CVEs for LiteLLM.


## [0.1.0] - 2026-04-29

Initial release of pazufa_corelib as a shared library for PaZuFa scrapers.

### Added

- **Project scaffold** — basic Python library structure with Poetry, dev tooling, and GitHub Actions CI (#2)
- **OpenAPI model** — auto-generated Pydantic v2 models from the PaZuFa OpenAPI v0.2.3 spec; pinned independently of project version (#3, #4)
- **LLMConnector** — base class for LLM interaction via LiteLLM, with retry logic, jitter, timeout handling, and detailed logging
- **Structured extraction** — `extract()` method for structured LLM output using Instructor (#15)
- **Enrichment models** — Pydantic models for enriched parliamentary data (#17)
- **Woodpecker CI** — CI pipeline for automated testing (#19)
- **Section extraction** — `extract_relevant_section()` method for targeted LLM extraction (#25)
- **Error classification** — provider errors classified inside `InstructorRetryException` (#27)
- **Token-based rate limiting** — TPM rate limiter in LLMConnector (#31)
- **Expert extraction** — `ExtractedExpert` / `ExpertenResult` models and `EXPERTEN_PROMPT` (#52)
- **Structured summarisation** — aligned Instructor calling with `from_provider`, wired summarise methods to `extract()` (#49)
- **Normalization module** (`pazufa_corelib/normalization`) — functions for normalising dates, URLs, free-text fields, hashes, and Schlagworte (tags + Sachgebiete) with fuzzy matching via RapidFuzz (#59)
- `pazufa_corelib.format_if_modified_since(dt)` — helper that formats a timezone-aware `datetime` into the exact string shape the API expects in the `If-Modified-Since` header (#73).


### Fixed

- Removed `generate_text()` regression; wired summarise methods correctly to `extract()` to restore CI (#69)
- Synced line-length config between Black and isort (#18)

### Changed

- Renamed internal modules for consistency (`chore/renaming`, #64)
- Renamed import name `corelib` → `pazufa_corelib` to align with the PyPI distribution name. Update imports from `from corelib...` to `from pazufa_corelib...`. PEP 503 normalization keeps `pip install pazufa-corelib` working alongside the canonical underscore form (#77).
- **`vg_ident_typ` is no longer an enum.** The previously-allowed values (`initdrucks`, `vorgnr`, `api-id`, `sonstig`) are now enforced socially via the schema description only; the API will accept any string. Downstream consumers that switched on these values should treat unknown identifier types as `sonstig` (#73).
