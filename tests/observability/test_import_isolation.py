"""Import wiring of ``pazufa_corelib.observability``.

The SDK must only be loaded when an application asks for ``configure`` or
``LoggingSpanExporter``; library imports stay on the API (or nothing).
"""

import importlib
import subprocess
import sys

import pytest

import pazufa_corelib.observability as obs


def _run_isolated(code: str) -> str:
    """Run code in a fresh interpreter so sys.modules is not shared with pytest."""
    result = subprocess.run(  # noqa: S603  # code is a hardcoded test snippet
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.mark.parametrize(
    "import_stmt",
    [
        "import pazufa_corelib",
        "import pazufa_corelib.llm",
        "import pazufa_corelib.observability",
        "from pazufa_corelib.observability import span, TraceContextFilter",
        "import pazufa_corelib.observability._configure",
    ],
)
def test_import_does_not_load_sdk(import_stmt: str) -> None:
    out = _run_isolated(
        f"{import_stmt}\n"
        "import sys\n"
        "print(any(m.startswith('opentelemetry.sdk') for m in sys.modules))"
    )
    assert out == "False"


def test_core_import_does_not_load_opentelemetry_at_all() -> None:
    out = _run_isolated(
        "import pazufa_corelib, pazufa_corelib.llm\n"
        "import sys\n"
        "print(sorted(m for m in sys.modules if m.startswith('opentelemetry')))"
    )
    assert out == "[]"


@pytest.mark.parametrize(
    ("name", "module"),
    [("configure", "_configure"), ("LoggingSpanExporter", "_log_exporter")],
)
def test_lazy_names_resolve_to_their_module(name: str, module: str) -> None:
    source = importlib.import_module(f"pazufa_corelib.observability.{module}")
    assert getattr(obs, name) is getattr(source, name)


def test_lazy_name_is_cached_in_module_globals() -> None:
    _ = obs.LoggingSpanExporter
    assert "LoggingSpanExporter" in vars(obs)


def test_unknown_attribute_raises() -> None:
    with pytest.raises(AttributeError, match="no_such_name"):
        _ = obs.no_such_name  # type: ignore[attr-defined]


def test_missing_sdk_gives_install_hint() -> None:
    out = _run_isolated(
        "import sys\n"
        "sys.modules['opentelemetry.sdk'] = None\n"
        "import pazufa_corelib.observability as obs\n"
        "try:\n"
        "    obs.LoggingSpanExporter\n"
        "except ImportError as exc:\n"
        "    print(exc)\n"
    )
    assert "pazufa_corelib[otel-otlp]" in out


def test_is_available_with_api_installed() -> None:
    assert obs.is_available() is True
