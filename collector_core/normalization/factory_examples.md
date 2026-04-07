# SchlagwortResolver — Factory Examples

The `SchlagwortResolver` exposes annotated Pydantic types (`TagList`,
`SachgebietList`) that can be used as field types in dynamically built
response models for LLM calls via [Instructor](https://python.useinstructor.com/).

---

## Tag Factory

```python
from pydantic import create_model, Field
from collector_core.normalization.schlagworte import SchlagwortResolver

def make_tag_model(resolver: SchlagwortResolver) -> type:
    return create_model(
        "TagResult",
        schlagworte=(
            resolver.TagList,
            Field(
                description=(
                    "Tags aus der bereitgestellten Liste, die auf dieses Dokument zutreffen."
                )
            ),
        ),
    )
```

**Prompt injection:**

```python
prompt = TAG_PROMPT.format(
    tags_list=resolver.get_tags_json(),
    ...
)
```

`get_tags_json()` returns a JSON array of `{"id": "...", "description": "..."}` objects
covering global tags, Sachgebiete (numbers excluded), and any local tags supplied at
construction time.

---

## Sachgebiet Factory

```python
from pydantic import create_model, Field
from collector_core.normalization.schlagworte import SchlagwortResolver

def make_sachgebiete_model(resolver: SchlagwortResolver) -> type:
    return create_model(
        "SachgebieteResult",
        sachgebiete=(
            resolver.SachgebietList,
            Field(
                description=(
                    "Sachgebiete aus der bereitgestellten Liste, die auf dieses Dokument zutreffen."
                )
            ),
        ),
    )
```

**Prompt injection:**

```python
prompt = SACHGEBIETE_PROMPT.format(
    sachgebiete_list=resolver.get_sachgebiete_no_numbers_json(),
    ...
)
```

`get_sachgebiete_no_numbers_json()` returns a JSON array of
`{"id": "...", "description": "..."}` objects — the `id` is the exact string the
LLM must return, the `description` provides semantic context.
The Parlamentsspiegel number is intentionally omitted so the LLM does not need
to know it.

---

## Extending an existing model

Use `__base__` to graft resolver validation onto a model that already exists.
The new field definition overrides the one from the base class; all other fields
and validators are inherited unchanged.

```python
from pydantic import create_model, Field
from collector_core.normalization.schlagworte import SchlagwortResolver
from collector_core.llm.models import SchlagworteResult

def extend_schlagworte_model(resolver: SchlagwortResolver) -> type:
    return create_model(
        "SchlagworteResult",
        __base__=SchlagworteResult,
        sachgebiete=(
            resolver.SachgebietList,
            Field(
                description=(
                    "Sachgebiete aus der bereitgestellten Liste, die auf dieses Dokument zutreffen."
                )
            ),
        ),
    )
```

The returned model behaves exactly like `SchlagworteResult` (same `schlagworte`
field, same model validators) but replaces the hardcoded `SACHGEBIETE_SET`
validator with the resolver's vocabulary. This is useful for migrating an
existing flow incrementally without rewriting the whole model.

---

## Notes

- `TagList` and `SachgebietList` are `Annotated[list[str], AfterValidator(...)]`
  types. Pydantic rejects any ID not present in the loaded vocabulary and
  Instructor will trigger a retry.
- Both factories should live in `collector_core/llm/models.py`.
- Instantiate the resolver once per scraper run and pass it to both the factory
  and the prompt formatter.