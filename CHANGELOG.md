# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---
## [Unreleased]
### Changed
- **api_model.py** — Is no longer completly automatically generated. It no contains Handwritten extensions
- **api_model.py** — Is now updated to spec 0.25
- **Naming of Some pydantic models** — In line with new naming in the API: `Scope` zu `ApiKeyScope`,`TouchedByItem` zu `TouchedByEntry`,`EnumerationNames` zu `EnumerationName`,`Lobbyregeintrag` zu `Lobbyregistereintrag`,
- **`openapi.yaml` updated to spec 0.2.5** (from 0.2.3, tag `v0.2.5+v0.0.7`) and `pazufa_corelib/api_client/` regenerated from it. The spec moved to OpenAPI 3.1.0 and renamed every schema to PascalCase; generated module and class names are unaffected because the generator normalises them.
- **`Dokument.hash` is now `oneOf[string, DokumentHash[]]`** — the plain hex string collectors already send stays valid, so this is additive for them. The structured arm carries `value` + `strategy` + `mime`, matching the variants `pazufa_corelib.normalization.hash` already returns.
- **Path parameters `{sid}` and `{vorgang_id}` are now `{api_id}`** — `sitzung`/`vorgang` by-id endpoints take `api_id=` instead.
- **The `If-Modified-Since` header is now spelled `if_modified_since`** on the wire. Underscores make this a different header, not a case variant; mirrored as the spec declares it and pinned by a test. Suspected upstream artifact — see below.

### Fixed
- **Serialization errors** — fixed multiple serialization errors, especially when exporting to JSON. 
- **Empty Strings exported**
- **Two endpoints no longer disappear from the generated client.** Spec 0.2.5 declares the `GET /api/v2/autoren` filters as `in: path` even though `/api/v2/autoren` has no path placeholders, and types the `DELETE /api/v2/auth` header as an object wrapper. Both are invalid as written and made `openapi-python-client` skip the whole endpoint. `tools/generate_openapi_client.py` now normalises them (query parameters / unwrapped scalar header) at generation time; the file on disk is untouched. Both should be fixed upstream.

### Added
- **_api_model_generated.py** — private new location of automatically generated pydantic models
- **_api_model_hardening.py** — private module used for hardening in api_model.py 
- **`PaZuFaBaseModel`** — PaZuFa specific child of the pydantic BaseModel
- **New 0.2.5 model surface** — `Vorgang.ressort` (`Ressort`) and `Vorgang.sachgebiete` (`Sachgebiet`), `Dokument.subdoc_id` for sections that legitimately share a hash, `DokumentHash`/`HashStrategy`/`Mime`, and `Zusammenfassungstupel` for typed partial summaries.
- **New enum values** — `Doktyp`: `eckpunktepapier`, `gesetz`. `Stationstyp`: `parl-antragsst`, `parl-verfgstop`, `parl-vermittas`, `preparl-formvs`.

### Removed
- **`Station.trojanergefahr`** — dropped by spec 0.2.5. Collectors that scored documents for it (the BW scraper does) have nowhere to put the value.
- **`X-Scraper-Id` on `PUT /api/v2/kalender/{parlament}/{datum}`** — dropped by spec 0.2.5 while `PUT /api/v2/vorgang` kept it, so `kal_date_put()` no longer accepts `x_scraper_id`. Looks accidental upstream.
- **`GET /ping` and `GET /status`** — removed from the spec, so `api/unauthorisiert/` is gone from the client.

### Deprecated
- **Old Naming of some pydantic models** — `Scope`;`TouchedByItem` ,`EnumerationNames`,`Lobbyregeintrag`

## [0.1.2] - 2026-06-16

### Changed

- **Summarization prompts reframed for the public** — `ZUSAMMENFASSUNG_PROMPT` and `ZUSAMMENFASSUNG_GESETZENTWURF_PROMPT` now state that the summary is shown on a public website that makes parliamentary proceedings accessible to citizens without legal/political background, ask for plain language with brief explanations of technical terms, and instruct the model to output only the summary itself. The explicit word-count target was dropped in favour of structural guidance (`focus on the essentials; as short as possible, as detailed as necessary`), since LLMs follow type/audience framing more reliably than numeric length targets.

### Fixed

- **`normalize_volltext` now strips C0 control characters and DEL** (`\x00`–`\x1f` except `\t \n \r`, plus `\x7f`). A stray NUL byte (`0x00`) previously survived into the output and caused the backend's PostgreSQL `text` insert to fail with `invalid byte sequence for encoding `UTF8`: 0x00` (#101).
- **Summary prompt/schema leakage** ([#104](https://codeberg.org/PaZuFa/pazufa-scraper-core/issues/104)) — `ZusammenfassungResult` no longer accepts output that merely echoes the task or response schema (e.g. summaries containing the `150-250 Wörter` length hint). A new `field_validator` rejects such prompt-echo output so Instructor re-prompts the model. A minimum summary length of 50 characters now drops truncated output, but it is relaxed when the caller requested short output via `LLMConnector.summarize`'s count parameters (signalled through the validation context), so length-bounded summaries keep working. The `150-250 word` instruction was removed from the schema field description (the most-parroted source); the defensive echo patterns are scoped (the length-hint pattern requires the `Wörter` unit, the meta-framing pattern is anchored to the start) so genuine numeric ranges and phrasings inside a real summary are not falsely rejected.

### Security

- **Bumped vulnerable transitive dependencies** to their fixed releases so `pip-audit` passes again: `aiohttp` 3.13.5 → 3.14.1 (multiple CVEs), `cryptography` 48.0.0 → 49.0.0 (`GHSA-537c-gmf6-5ccf`), and `pip` 26.1.1 → 26.1.2 (`PYSEC-2026-196`). The remaining `diskcache` advisory (`CVE-2025-69872`) has no upstream fix and stays ignored, tracked in issue #97.

## [0.1.1] - 2026-05-30

### Added

- **`AuthorResolver`** (`pazufa_corelib/normalization/names.py`) — fuzzy author-name resolver backed by a YAML vocabulary. Supports `resolve()`, `resolve_batch()`, `get_author_by_id()`, `check_author()`, `fuzzy_check_author()`, and `explain()` for diagnostics. Configurable `match_threshold`; aliases and umlaut folding handled automatically.
- **`OrganizationResolver`** — cosine-similarity resolver for organization names, with configurable `match_threshold` and `near_tie_epsilon`. Exposes `resolve()`, `resolve_batch()`, `get_organization_by_id()`, `check_organization()`, and `explain()`.
- **`names_model`** (`pazufa_corelib/names_model.py`) — Pydantic models `Author`, `Organization`, `AuthorFile`, `AuthorIDResolution`, and `NameIDResolution` for the author/organization normalization chain.
- **Global YAML vocabularies** under `pazufa_corelib/normalization/mappings/`: `authors.yaml`, `organizations.yaml`, and `parteien.yaml` (political parties).
- **`normalize_autor`** — experimental high-level function that combines `AuthorResolver` and `OrganizationResolver` to resolve a raw author string to a canonical name and ID.
- **`SchlagwortResolver.canonicalise_tag`** — single-value tag canonicalization helper. Returns `str | None`; unresolved or blank results are coerced to `None` and logged as a warning.
- **`SchlagwortResolver.canonicalise_sachgebiet`** — single-value Sachgebiet canonicalization helper. Returns `str | None` with the same blank-to-`None` coercion and warning behavior.
- **`SchlagwortResolver.explain`** — diagnostic trace of a tag query (processed query, exact-match flag, threshold, near-tie epsilon, top-K fuzzy candidates).
- **YAML validator tools** (`tools/`) — three CLI scripts for pre-merge conflict detection:
  - `yaml_validator_authors.py` — checks ID collisions, exact `canonical_name` collisions, and fuzzy near-matches against the global author vocabulary.
  - `yaml_validator_organizations.py` — same checks for organizations using cosine similarity.
  - `yaml_validator_tags.py` — checks tag ID collisions and fuzzy ID near-matches against the global tag vocabulary.
  - All tools accept positional `extra_files` for unreleased context files and support `--match-threshold` / `--near-tie-epsilon` flags.
- **`SETUP_NORMALIZATION.md`** — step-by-step guide for extending the author, organization, and tag/Sachgebiet vocabularies, including YAML format reference, usage examples, and validator instructions.
- **`Makefile`** — common development commands (`make check`, `make test`, `make lint`, etc.).
- **Compliance** — licenses of the packages are now automatically checked in CI.

### Changed
- **`SchlagwortResolver` — configurable thresholds** — `__init__` now accepts `match_threshold` (default 90) and `near_tie_epsilon` (default 1.0), forwarded to all internal fuzzy operations and reflected in `explain()` traces.
- **`_canonicalise_ids` — configurable `near_tie_epsilon`** — the private helper now accepts a `near_tie_epsilon` parameter (default `_NEAR_TIE_EPSILON`) instead of always using the module constant.
- **Supported Python versions** — dropped support for Python 3.14, as the new LiteLLM Versions do not support it.

### Experimental
- **'normalize_autor'** — Normalize the ``organisation`` and ``person`` fields of an Autor in-place. Resolves each field against the provided resolvers and updates it to the
    canonical name if a match is found; logs debug information otherwise. (Experimental, due to open decion if such a function should be part of the Corelib or only of the -based Implementations [planned for v0.2])

### Fixed

- Bug fixes in author normalization logic and associated tests.
- Bug fix, python-dateutil now explicitly named as a dependency.
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
