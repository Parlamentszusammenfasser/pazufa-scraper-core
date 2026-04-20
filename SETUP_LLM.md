# LLM setup

`corelib.llm` provides Pydantic response models, prompt templates, and
the Parlamentsspiegel Sachgebiete taxonomy for LLM-based enrichment of
parliamentary documents.

Full reference (models, prompts, taxonomy, section extraction) lives on the
wiki: <https://wiki.pazufa.de/books/scraper-core/page/llm>.

## Minimal example

`LLMConnector` uses [litellm](https://docs.litellm.ai/docs/providers) under the
hood — set the API key for your chosen provider in the environment, e.g.
`export OPENAI_API_KEY="sk-..."`.

```python
from corelib import LLMConnector

connector = LLMConnector(model="openai/gpt-4o-mini", temperature=0.1)

zusammenfassung = await connector.summarize_dokument(titel=titel, text=text)
```
