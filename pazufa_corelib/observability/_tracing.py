"""Span helper that degrades to a no-op without OpenTelemetry.

Only depends on ``opentelemetry-api`` (extra ``otel``). Without an SDK
configured by the application, the API itself is a no-op, so spans here are
cheap enough for library code.
"""
