# LLM module setup

`corelib.llm` uses [litellm](https://docs.litellm.ai) under the
hood, which means that [any LLM provider supported by litellm](https://docs.litellm.ai/docs/providers) can be used.

## Configuring the API key

Set the API key for your chosen provider as an environment variable:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Or e.g. Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

Alternatively, the key can be passed directly to the `LLMConnector`:

```python
from corelib import LLMConnector

connector = LLMConnector(model="openai/gpt-4o-mini", api_key="sk-...")
```

## Further documentation

Detailed information on models, prompts, taxonomy, and section extraction is
available on the wiki:
<https://wiki.pazufa.de/books/scraper-core/page/llm>.
