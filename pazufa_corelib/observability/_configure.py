"""Application-side OpenTelemetry setup for scrapers.

Needs the ``otel-otlp`` extra. SDK and exporter modules are imported inside
``configure()`` so that importing this module stays cheap.
"""

