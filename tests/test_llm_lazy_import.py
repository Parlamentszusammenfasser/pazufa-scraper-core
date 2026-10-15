"""Tests for lazy loading of the LLM connector in ``pazufa_corelib.llm``."""

import subprocess
import sys

import pytest

import pazufa_corelib.llm as llm_pkg


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
        "from pazufa_corelib.llm import ZusammenfassungResult",
        "from pazufa_corelib.llm import ZUSAMMENFASSUNG_PROMPT",
        "import pazufa_corelib.llm.models",
        "import pazufa_corelib.llm.prompts",
    ],
)
def test_import_does_not_load_litellm(import_stmt: str) -> None:
    out = _run_isolated(
        f"{import_stmt}\n"
        "import sys\n"
        "print('litellm' in sys.modules, 'instructor' in sys.modules)"
    )
    assert out == "False False"


def test_connector_access_loads_litellm() -> None:
    out = _run_isolated(
        "import sys\n"
        "from pazufa_corelib.llm import LLMConnector\n"
        "print(LLMConnector.__name__, 'litellm' in sys.modules)"
    )
    assert out == "LLMConnector True"


@pytest.mark.parametrize("name", sorted(llm_pkg._LAZY_CONNECTOR_NAMES))
def test_lazy_names_resolve_to_connector_module(name: str) -> None:
    from pazufa_corelib.llm import llm_connector

    assert getattr(llm_pkg, name) is getattr(llm_connector, name)
    assert name in llm_pkg.__all__


def test_lazy_name_is_cached_in_module_globals() -> None:
    _ = llm_pkg.LLMConnector
    assert "LLMConnector" in vars(llm_pkg)


def test_unknown_attribute_raises() -> None:
    with pytest.raises(AttributeError, match="no_such_name"):
        _ = llm_pkg.no_such_name  # type: ignore[attr-defined]
