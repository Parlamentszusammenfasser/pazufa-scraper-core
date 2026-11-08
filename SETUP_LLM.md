# LLM module setup

`pazufa_corelib.llm` uses [litellm](https://docs.litellm.ai) under the
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
from pazufa_corelib import LLMConnector

connector = LLMConnector(model="openai/gpt-4o-mini", api_key="sk-...")
```

## Token usage

Each connector sums the tokens its successful calls used, as reported by the
provider (`0` if the provider reports none):

```python
connector.model              # e.g. "openai/gpt-4o-mini"
connector.prompt_tokens      # input tokens so far
connector.completion_tokens  # output tokens so far
```

## Further documentation

Detailed information on models, prompts, taxonomy, and section extraction is
available on the wiki:
<https://wiki.pazufa.de/books/scraper-core/page/llm>.
