# collector_core.enrichment

Shared Pydantic response models, prompt templates, and the Parlamentsspiegel
Sachgebiete taxonomy for LLM-based enrichment of parliamentary documents.

Designed for use with `LLMConnector.extract()` from `collector_core`.

## Quick start

```python
import asyncio
from collector_core import LLMConnector
from collector_core.enrichment import (
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

async def enrich(text: str, titel: str) -> None:
    connector = LLMConnector(model="openai/gpt-4.1-nano", temperature=0.1)

    # Zusammenfassung
    prompt = ZUSAMMENFASSUNG_PROMPT.format(titel=titel, text=text[:8000])
    result = await connector.extract(prompt=prompt, response_model=ZusammenfassungResult)
    print(result.zusammenfassung)

    # Schlagworte (with taxonomy validation)
    prompt = SCHLAGWORTE_PROMPT.format(
        sachgebiete_list=format_sachgebiete_list(),
        vorgang_titel=titel,
        vorgang_vnr="8/1234",
        dok_typ="Gesetzentwurf",
        titel=titel,
        text=text[:5000],
    )
    result = await connector.extract(prompt=prompt, response_model=SchlagworteResult)
    print(result.sachgebiete)   # validated against taxonomy
    print(result.schlagworte)   # free-form keywords
```

## Models

Each model is a standalone Pydantic `BaseModel` for use with `LLMConnector.extract()`.

| Model | Fields | Notes |
|-------|--------|-------|
| `KurztitelResult` | `kurztitel` | Short, plain-language title (5-10 words) |
| `ZusammenfassungResult` | `zusammenfassung` | Compact summary covering goal, key measures, changed laws/articles, costs, and background where available |
| `SchlagworteResult` | `sachgebiete`, `schlagworte` | `field_validator` rejects Sachgebiete not in the taxonomy (triggers Instructor retry) |
| `MeinungResult` | `meinung`, `begruendung` | `meinung` is `Literal[1,2,3,4,5]` — best suited for Stellungnahmen and Beschlussempfehlungen |
| `VerfassungsaenderndResult` | `ist_verfassungsaendernd`, `begruendung` | Bool + reasoning; prompt uses `{land}` so each scraper specifies its state |

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
- Text truncation limits
- Caching strategy
- Pre-filters (e.g. keyword check before Verfassungsändernd)
- Error handling and retry logic beyond Instructor's built-in retries
