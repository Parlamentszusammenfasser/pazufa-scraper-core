"""
collector_core - Core library for collecting parliamentary data
"""

from .llm_connector import (
    LLMAuthenticationError,
    LLMConnector,
    LLMConnectorError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResponseParseError,
    LLMTemporaryProviderError,
    LLMValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "LLMConnector",
    "LLMConnectorError",
    "LLMResponseParseError",
    "LLMProviderError",
    "LLMAuthenticationError",
    "LLMQuotaExceededError",
    "LLMRateLimitError",
    "LLMTemporaryProviderError",
    "LLMValidationError",
]
