"""Span exporter that writes one readable log line per finished span.

Needs the ``otel-otlp`` extra. Only imported lazily through
``pazufa_corelib.observability.__getattr__``, which is why the module-level SDK
import is allowed here.
"""

