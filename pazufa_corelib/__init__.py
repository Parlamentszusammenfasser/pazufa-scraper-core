"""pazufa_corelib - Core library for collecting parliamentary data.

LLM enrichment functionality is available via the ``pazufa_corelib.llm``
subpackage (models, prompts, taxonomy, and connector).
"""

from importlib.metadata import PackageNotFoundError, version

from pazufa_corelib.api_helpers import format_if_modified_since

try:
    __version__ = version("pazufa_corelib")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "__version__",
    "format_if_modified_since",
]
