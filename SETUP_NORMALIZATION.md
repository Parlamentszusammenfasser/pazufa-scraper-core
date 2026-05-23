# SETUP_NORMALIZATION.md — Extending the Normalization Vocabularies

This document explains how to add entries to the three normalization vocabularies:
**Autoren**, **Organisationen**, and **Schlagwörter** (Tags + Sachgebiete).

---

## Overview

The built-in mappings live under `pazufa_corelib/normalization/mappings/`:

| File | Loaded by |
|------|-----------|
| `authors.yaml` | `AuthorResolver` |
| `parteien.yaml`, `organizations.yaml` | `OrganizationResolver` (merged in order) |
| `global_tags.yaml` | `SchlagwortResolver` |
| `sachgebiete.yaml` | `SchlagwortResolver` |

All resolvers accept **caller-supplied extra files** that are merged on top of the built-in mappings. You do not need to touch the library's own files.

---

## Autoren

### YAML format

```yaml
names:
  - id: mueller-maria
    canonical_name: Maria Müller
    aliases:
      - Müller, Maria
      - Dr. Maria Müller MdB

  - id: schmidt-hans
    canonical_name: Hans Schmidt
    aliases:
      - Schmidt, Hans
      - Dr. Hans Schmidt
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique slug — letters (incl. umlauts), digits, hyphens, underscores. First character must be a letter or digit. |
| `canonical_name` | yes | Display name used as the resolved output. |
| `aliases` | no | Alternative spellings the resolver should accept. |

**Alias tips:**
- The resolver strips honorifics (`Dr.`, `Prof.`, `MdB`, …) and token-sorts before matching, so `Dr. Maria Müller MdB` and `Müller, Maria` already collapse to the same key internally. Add an alias only when a surface form has a genuinely different structure that would not survive that normalization (e.g. a birth name, a nickname, or a non-obvious abbreviation).
- Umlaut variants (`Mueller` ↔ `Müller`) are folded automatically — no alias needed.

### Using extra author files

```python
from pathlib import Path
from pazufa_corelib.normalization import AuthorResolver

resolver = AuthorResolver(files=[Path("my_authors.yaml")])
```

Later files override earlier ones when IDs collide, so you can use an extra file to override a built-in entry.

---

## Organisationen

Organizations are split across two built-in files (`parteien.yaml` for political parties, `organizations.yaml` for everything else) and merged in that order. Extra files are appended after both.

**Built-in party entries** (`parteien.yaml`) use the short acronym as both `canonical_name` and `acronym`. CDU, CSU, and the parliamentary CDU/CSU Fraktion are separate entries (`cdu`, `csu`, `cdu-csu`).

### YAML format

```yaml
names:
  - id: bundesministerium-finanzen
    canonical_name: Bundesministerium der Finanzen
    acronym: BMF
    aliases:
      - Finanzministerium
      - BMF
      - Bundesfinanzministerium

  - id: landesbank-bw
    canonical_name: Landesbank Baden-Württemberg
    acronym: LBBW
    aliases:
      - LBBW
      - Landesbank BW

  - id: some-org-without-acronym
    canonical_name: Irgendeine Organisation
    acronym:
    aliases: []
```

> **`acronym` is required** — every entry must declare it. Use `acronym:` (bare key, YAML null) for entries without an abbreviation. Omitting the key entirely raises a validation error at load time.

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique slug — same rules as for authors. |
| `canonical_name` | yes | Display name used as the resolved output. |
| `acronym` | yes | Short-form abbreviation (e.g. `BMF`), or `null` if none. Must always be present — write `acronym:` or `acronym: null` for entries without one. |
| `aliases` | no | Alternative names and spellings. |

**Matching notes:**
- `OrganizationResolver` uses character n-gram cosine similarity, which is robust to word-order differences and long compound names. Aliases primarily help exact lookup; fuzzy matching works without them for close variants.
- The acronym is not used for matching — list it as an alias if it should be resolvable.

> **Footgun — what an alias actually becomes:** Write aliases as plain human-readable strings; do not try to pre-format them to match the internal lookup key. Every alias passes through `normalize_name_key` (NFKC → strip invisibles → lowercase → umlaut fold `ü→ue` `ö→oe` `ä→ae` `ß→ss` → strip punctuation → collapse whitespace) and is then token-sorted before comparison. So an alias `Fraktion GRÜNE` does **not** become `fraktiongrüne` — it becomes `fraktion gruene` (lower-cased, umlaut-folded, with the inter-token space preserved). Two implications:
>
> - Do not write `fraktiongruene` or `Fraktion Gruene` thinking you are "helping" the resolver; the original `Fraktion GRÜNE` already collapses to the same key.
> - Umlaut and casing variants (`Grüne` ↔ `GRUENE` ↔ `gruene`) are folded automatically — adding all three as aliases is redundant.

### Using extra organization files

```python
from pathlib import Path
from pazufa_corelib.normalization import OrganizationResolver

resolver = OrganizationResolver(files=[Path("my_orgs.yaml")])
```

---

## Schlagwörter

The vocabulary has two distinct parts loaded by `SchlagwortResolver`:

- **Tags** — free-form labels with optional descriptions (`global_tags.yaml`).
- **Sachgebiete** — numbered topic taxonomy entries (`sachgebiete.yaml`).

### Tag YAML format

```yaml
tags:
  - id: Digitalisierung
    description: E-Government, digitale Infrastruktur, IT-Sicherheit und digitale Verwaltungsdienstleistungen

  - id: Wohnungsbau
    description: Sozialer Wohnungsbau, Mietpreisbremse, Wohnraumförderung und Baulandmobilisierung
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Human-readable label — letters (incl. umlauts), spaces, and hyphens only. No digits or special characters. Must start with a letter. |
| `description` | no | Context for humans and LLMs; helps classification quality. |

### Sachgebiet YAML format (`sachgebiete.yaml` only)

```yaml
tags:
  - id: Staat und Politik
    number: 1000
    description: Grundlagen des Staatswesens, politische Systeme und demokratische Prozesse

  - id: Digitale Infrastruktur
    number: 4050
    description: Breitbandausbau, Glasfaser und Mobilfunkversorgung
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Same rules as Tags. |
| `number` | yes | Positive integer; unique within the Sachgebiet vocabulary. |
| `description` | no | Context for humans and LLMs. |

> **Note:** Sachgebiete cannot be extended via extra files — only the built-in `sachgebiete.yaml` is loaded. This is intentional,
> as the vocabulary is not meant to be extended by users.

### Using extra tag files (local Tags only)

```python
from pathlib import Path
from pazufa_corelib.normalization.schlagworte import SchlagwortResolver

resolver = SchlagwortResolver(local_tags=[Path("my_tags.yaml")])
```

**Load priority** (lowest → highest):

1. Local tags (caller-supplied) — overridden by global if IDs collide
2. Global tags (`global_tags.yaml`)
3. Sachgebiete (`sachgebiete.yaml`)

---

## Validating New Files Before Merging

Before committing a new mapping file, run the appropriate validator tool against it.
The validator checks the candidate file against whatever reference YAML files you pass on the command line — when none are passed, the built-in vocabulary files for that resolver are used. **Any files you pass replace the defaults**, so include the built-ins explicitly if you want them checked alongside your extras. The validator emits a warning to remind you which mode it ran in.

The validator catches three classes of problems:

| Check | Severity | Description |
|-------|----------|-------------|
| YAML schema | hard error | Malformed YAML or missing required fields |
| ID collision | hard error | The `id` already exists in the global vocabulary |
| Name / ID collision | hard error (authors/orgs) | `canonical_name` exactly matches an existing entry |
| Fuzzy collision | warning | Entry is so similar to an existing one that the resolver may confuse them |
| Intra-file fuzzy | warning | Two entries within the *new* file are too similar to each other |

Hard errors exit with code 1. Warnings are printed but do not fail the run — review them manually and decide whether to accept the similarity or adjust the entry.

### Authors

```bash
poetry run python -m tools.yaml_validator_authors my_authors.yaml
# validate against a custom reference set (replaces the built-in AUTHORS_FILES):
poetry run python -m tools.yaml_validator_authors my_authors.yaml already_merged.yaml
# tune the fuzzy threshold (0–100, default 90):
poetry run python -m tools.yaml_validator_authors my_authors.yaml --match-threshold 85
```

### Organizations

```bash
poetry run python -m tools.yaml_validator_organizations my_orgs.yaml
poetry run python -m tools.yaml_validator_organizations my_orgs.yaml already_merged.yaml
# tune both thresholds:
poetry run python -m tools.yaml_validator_organizations my_orgs.yaml \
    --match-threshold 85 --near-tie-epsilon 1.0
```

### Tags

```bash
poetry run python -m tools.yaml_validator_tags my_tags.yaml
poetry run python -m tools.yaml_validator_tags my_tags.yaml already_merged.yaml
poetry run python -m tools.yaml_validator_tags my_tags.yaml \
    --match-threshold 85 --near-tie-epsilon 1.0
```

### Calling the validators from Python

The same checks are available as plain functions — useful for pre-commit hooks, custom test suites, or batch validation. Each validator lives in its own module under ``tools``:

```python
from pathlib import Path

from tools.yaml_validator_authors import yaml_validator_authors
from tools.yaml_validator_organizations import yaml_validator_organizations
from tools.yaml_validator_tags import yaml_validator_tags

# Default: check against the built-in vocabulary files for that resolver.
yaml_validator_authors(Path("my_authors.yaml"))

# Custom reference set (replaces the built-in defaults entirely):
yaml_validator_organizations(
    Path("my_orgs.yaml"),
    files=[Path("already_merged.yaml")],
)

# Tune thresholds the same way as the CLI flags:
yaml_validator_tags(
    Path("my_tags.yaml"),
    match_threshold=85,
    near_tie_epsilon=1.0,
)
```

Each function raises ``ValueError`` on hard errors (schema problems, ID/name collisions) and ``FileNotFoundError`` if the candidate path is missing. Warnings (fuzzy / intra-file collisions, default-vs-custom reference set) are printed to stdout — the call returns ``None`` on success.

**Notes:**
- If the file you are validating also appears in the reference `files` list it is silently removed to prevent false self-matches.
- Positional `files` arguments **replace** the built-in defaults (`AUTHORS_FILES`, `ORGANIZATIONS_FILES`, `TAGS_FILES`). The validator prints a warning indicating which set was used. To extend rather than replace, pass the built-ins explicitly alongside your extras.
- The organization validator uses cosine similarity on character n-grams; the author and tag validators use fuzzy token-sort-ratio. Default `--match-threshold`: **80** for organizations, **90** for authors and tags.
- Tags are matched on their `id` string directly (not a `canonical_name`), so the fuzzy check compares raw ID strings.
- As mentioned above, the Sachgebiete vocabulary is not meant to be extended by users therefore, no validation tool exists for related mapping files.

---

## ID Rules Summary

| Vocabulary | Pattern | Example |
|------------|---------|---------|
| Author `id` | `[A-ZÄÖÜa-zäöüß0-9][A-ZÄÖÜa-zäöüß0-9\-_]+` | `mueller-maria` |
| Organization `id` | same as Author | `bundesministerium-finanzen` |
| Tag / Sachgebiet `id` | `[A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß\s\-]+` (no digits) | `Digitale Infrastruktur` |

Duplicate IDs within a file raise `ValueError` at load time.

---

## Testing Your Additions

Run the validator first (see [Validating New Files Before Merging](#validating-new-files-before-merging)) to catch collisions automatically.

For manual spot-checks after loading, use `resolve` / `explain`:

```python
from pathlib import Path
from pazufa_corelib.normalization import AuthorResolver, OrganizationResolver

author_resolver = AuthorResolver(files=[Path("my_authors.yaml")])
r = author_resolver.resolve("Dr. Maria Müller")
print(r.resolved_id, r.canonical_name, r.score)

org_resolver = OrganizationResolver(files=[Path("my_orgs.yaml")])
print(org_resolver.explain("Finanzministerium", k=3))
```

For Tags:

```python
from pathlib import Path
from pazufa_corelib.normalization.schlagworte import SchlagwortResolver

resolver = SchlagwortResolver(local_tags=[Path("my_tags.yaml")])
print(resolver.check_tag("Digitalisierung"))   # exact lookup
print(resolver.explain("Digitalisierungs", k=3))  # fuzzy trace
```