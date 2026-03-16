# collector_core.llm

Shared Pydantic response models, prompt templates, and the Parlamentsspiegel
Sachgebiete taxonomy for LLM-based enrichment of parliamentary documents.

Designed for use with `LLMConnector.extract()` from `collector_core`.

## Quick start

```python
import asyncio
from collector_core import LLMConnector
from collector_core.llm import (
    SCHLAGWORTE_PROMPT,
    ZUSAMMENFASSUNG_PROMPT,
    SchlagworteResult,
    ZusammenfassungResult,
    format_sachgebiete_list,
)

# LLMConnector uses litellm under the hood. The API key for your chosen
# provider must be set in the environment, e.g.:
#   export OPENAI_API_KEY="sk-..."
# See https://docs.litellm.ai/docs/providers for supported providers.

async def enrich(volltext: str, titel: str, vorgang_vnr: str) -> None:
    connector = LLMConnector(model="openai/gpt-4o-mini", temperature=0.1)

    # Step 1: Extract the relevant section from long documents.
    # Short documents pass through unchanged; long documents (e.g.
    # plenary protocols with many agenda items) are chunked and only
    # the section relevant to the Vorgang is returned.
    text = await connector.extract_relevant_section(
        text=volltext,
        vorgang_titel=titel,
        vorgang_vnr=vorgang_vnr,
    )
    if text is None:
        print("No relevant content found in document")
        return

    # Step 2: Enrich the (now right-sized) text
    # Zusammenfassung
    prompt = ZUSAMMENFASSUNG_PROMPT.format(titel=titel, text=text)
    result = await connector.extract(prompt=prompt, response_model=ZusammenfassungResult)
    print(result.zusammenfassung)

    # Schlagworte (with taxonomy validation)
    prompt = SCHLAGWORTE_PROMPT.format(
        sachgebiete_list=format_sachgebiete_list(),
        vorgang_titel=titel,
        vorgang_vnr=vorgang_vnr,
        dok_typ="Gesetzentwurf",
        titel=titel,
        text=text,
    )
    result = await connector.extract(prompt=prompt, response_model=SchlagworteResult)
    print(result.sachgebiete)   # validated against taxonomy
    print(result.schlagworte)   # free-form keywords
```

## Section extraction

Parliamentary protocols often contain many agenda items, but a scraper
typically processes one Vorgang at a time. Full protocols can exceed 100K
tokens — beyond the context window of many models.

`LLMConnector.extract_relevant_section()` solves this:

- **Short documents** (below `token_threshold`, default 30K tokens) pass
  through unchanged.
- **Long documents** are split into overlapping chunks. For each chunk the
  LLM identifies relevant line ranges via structured extraction. The
  corresponding text is then extracted computationally from the source,
  **guaranteeing verbatim output** (the LLM never reproduces text — it only
  points to line numbers).

```python
text = await connector.extract_relevant_section(
    text=volltext,                # full document text
    vorgang_titel="Schulgesetz",  # title of the Vorgang to find
    vorgang_vnr="8/630",          # optional Drucksache/VNR for context
    token_threshold=30000,        # pass-through threshold (tokens)
    chunk_size=30000,             # chunk size (tokens)
    chunk_overlap=1000,           # overlap between chunks (tokens)
)
# Returns str (extracted text) or None (nothing relevant found)
```

**Recommended workflow:** Always call `extract_relevant_section()` before
passing text to enrichment prompts. For dedicated documents (Gesetzentwürfe,
Beschlussempfehlungen etc.) it will pass through unchanged. For plenary
protocols it extracts just the relevant debate — no manual truncation needed.

## Models

Each model is a standalone Pydantic `BaseModel` for use with `LLMConnector.extract()`.

| Model | Fields | Notes |
|-------|--------|-------|
| `KurztitelResult` | `kurztitel` | Short, plain-language title (5-10 words) |
| `ZusammenfassungResult` | `zusammenfassung` | Compact summary covering goal, key measures, changed laws/articles, costs, and background where available |
| `SchlagworteResult` | `sachgebiete`, `schlagworte` | `field_validator` rejects Sachgebiete not in the taxonomy (triggers Instructor retry) |
| `MeinungResult` | `meinung`, `begruendung` | `meinung` is `Literal[1,2,3,4,5]` — best suited for Stellungnahmen and Beschlussempfehlungen |
| `VerfassungsaenderndResult` | `ist_verfassungsaendernd`, `begruendung` | Bool + reasoning; prompt uses `{land}` so each scraper specifies its state |
| `LineRange` | `start`, `end` | Contiguous range of 1-based line numbers; used by `SectionExtractionResult` |
| `SectionExtractionResult` | `is_relevant`, `relevant_lines` | Per-chunk extraction result returned by the LLM; line ranges are validated (`start <= end`, `>= 1`) |

## Prompts

Each prompt is a `str.format()` template. Format variables are documented in
the module docstrings.

| Prompt | Format vars | Notes |
|--------|-------------|-------|
| `KURZTITEL_PROMPT` | `titel`, `abstract` | |
| `ZUSAMMENFASSUNG_PROMPT` | `titel`, `text` | Guides the LLM to cover Ziel, Maßnahmen, geänderte Vorschriften, Kosten, Inkrafttreten, Hintergrund — but only where present in the source text |
| `SCHLAGWORTE_PROMPT` | `sachgebiete_list`, `vorgang_titel`, `vorgang_vnr`, `dok_typ`, `titel`, `text` | Use `format_sachgebiete_list()` for `{sachgebiete_list}` |
| `MEINUNG_PROMPT` | `dok_typ`, `titel`, `text` | Scale: 1=Ablehnung … 5=Zustimmung |
| `VERFASSUNGSAENDERND_PROMPT` | `land`, `titel`, `schlagworte`, `text` | Distinguishes Landesverfassung from Kommunalverfassung |
| `SECTION_EXTRACTION_PROMPT` | `vorgang_titel`, `vorgang_vnr_part`, `text` | Used internally by `extract_relevant_section()`; `vorgang_vnr_part` is `" (Drucksache X/Y)"` or `""` |

## Taxonomy

163 Sachgebiete from the [Parlamentsspiegel taxonomy](https://codeberg.org/PaZuFa/parlamentsspiegel-docu),
excluding "Unbekannt" (9900) and "ohne@-Systematik" (9999).

- `SACHGEBIETE` — `tuple[tuple[int, str], ...]` with (code, name) pairs
- `SACHGEBIETE_NAMES` — `tuple[str, ...]` just the names
- `SACHGEBIETE_SET` — `frozenset[str]` for O(1) validation

## What stays scraper-side

The enrichment module provides models and prompts, not orchestration. Each
scraper decides:

- Which doc types get which enrichment (e.g. Meinung only for Stellungnahmen)
- Whether to call `extract_relevant_section()` (recommended for all multi-topic documents like plenary protocols; not needed for single-topic documents like Gesetzentwürfe, though it will harmlessly pass through)
- Caching strategy
- Pre-filters (e.g. keyword check before Verfassungsändernd)
- Error handling and retry logic beyond Instructor's built-in retries
