"""pazufa_corelib - Core library for collecting parliamentary data.

LLM enrichment functionality is available via the ``pazufa_corelib.llm``
subpackage (models, prompts, taxonomy, and connector).
"""

from pazufa_corelib.api_helpers import format_if_modified_since

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "format_if_modified_since",
]
