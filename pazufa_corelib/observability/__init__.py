"""Optional OpenTelemetry support for pazufa_corelib.

Library code only uses the API-level helpers (``span``, ``TraceContextFilter``),
which work without OpenTelemetry installed. Application-side setup
(``configure``, ``LoggingSpanExporter``) needs the ``otel-otlp`` extra and is
imported lazily on first access, so a plain install never loads the SDK.
"""


