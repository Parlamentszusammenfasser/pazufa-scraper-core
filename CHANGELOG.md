# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [0.1.0] - 2026-04-26

Initial release of scraper-core as a shared library for PaZuFa scrapers.

### Added

- **Project scaffold** — basic Python library structure with Poetry, dev tooling, and GitHub Actions CI (#2)
- **OpenAPI model** — auto-generated Pydantic v2 models from the PaZuFa OpenAPI spec; pinned independently of project version (#3, #4)
- **LLMConnector** — base class for LLM interaction via LiteLLM, with retry logic, jitter, timeout handling, and detailed logging
- **Structured extraction** — `extract()` method for structured LLM output using Instructor (#15)
- **Enrichment models** — Pydantic models for enriched parliamentary data (#17)
- **Woodpecker CI** — CI pipeline for automated testing (#19)
- **Section extraction** — `extract_relevant_section()` method for targeted LLM extraction (#25)
- **Error classification** — provider errors classified inside `InstructorRetryException` (#27)
- **Token-based rate limiting** — TPM rate limiter in LLMConnector (#31)
- **Expert extraction** — `ExtractedExpert` / `ExpertenResult` models and `EXPERTEN_PROMPT` (#52)
- **Structured summarisation** — aligned Instructor calling with `from_provider`, wired summarise methods to `extract()` (#49)
- **Normalization module** (`corelib/normalization`) — functions for normalising dates, URLs, free-text fields, hashes, and Schlagworte (tags + Sachgebiete) with fuzzy matching via RapidFuzz (#59)

### Fixed

- Removed `generate_text()` regression; wired summarise methods correctly to `extract()` to restore CI (#69)
- Synced line-length config between Black and isort (#18)

### Changed

- Renamed internal modules for consistency (`chore/renaming`, #64)