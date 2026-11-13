"""Metrics recorded by the normalization resolvers.

Each test swaps the module instruments for ones on a local ``MeterProvider``
with an in-memory reader: the global provider can only be set once per process.
Small YAML vocabularies keep exact, fuzzy and unresolved cases deterministic.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    HistogramDataPoint,
    InMemoryMetricReader,
    NumberDataPoint,
)

import pazufa_corelib.normalization.schlagworte as schlagworte_mod
from pazufa_corelib.normalization.authors import AuthorResolver
from pazufa_corelib.normalization.organizations import OrganizationResolver
from pazufa_corelib.normalization.schlagworte import SchlagwortResolver
from pazufa_corelib.observability import _metrics
from pazufa_corelib.observability._attributes import (
    METRIC_NORMALIZATION_DROPPED,
    METRIC_NORMALIZATION_MATCH_SCORE,
    METRIC_NORMALIZATION_NEAR_TIES,
    METRIC_NORMALIZATION_RESOLUTIONS,
    NORMALIZATION_OUTCOME,
    NORMALIZATION_RESOLVER,
    TRACER_NAME,
)

# --- Fixtures -----------------------------------------------------------------------


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> Iterator[InMemoryMetricReader]:
    memory = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[memory])
    instruments = _metrics._create_instruments(provider.get_meter(TRACER_NAME))
    monkeypatch.setattr(_metrics, "_INSTRUMENTS", instruments)
    yield memory
    provider.shutdown()


@pytest.fixture
def authors(tmp_path: Path) -> AuthorResolver:
    f = tmp_path / "authors.yaml"
    f.write_text(
        "names:\n"
        "  - id: olaf-scholz\n"
        "    canonical_name: Olaf Scholz\n"
        "    aliases: []\n"
        "  - id: anna-schmidt\n"
        "    canonical_name: Anna Schmidt\n"
        "    aliases: []\n"
        "  - id: anne-schmidt\n"
        "    canonical_name: Anne Schmidt\n"
        "    aliases: []\n",
        encoding="utf-8",
    )
    return AuthorResolver(files=[f])


@pytest.fixture
def organizations(tmp_path: Path) -> OrganizationResolver:
    f = tmp_path / "orgs.yaml"
    f.write_text(
        "names:\n"
        "  - id: spd\n"
        "    canonical_name: Sozialdemokratische Partei Deutschlands\n"
        "    acronym: SPD\n"
        "    aliases: []\n"
        "  - id: ausschuss-umwelt\n"
        "    canonical_name: Ausschuss für Umwelt\n"
        "    acronym:\n"
        "  - id: ausschuss-umwelt-2\n"
        "    canonical_name: Ausschuss für Umwelt II\n"
        "    acronym:\n",
        encoding="utf-8",
    )
    # "Ausschuss für Umwelt I" scores ~96 vs ~94 against the two committees.
    return OrganizationResolver(files=[f], near_tie_epsilon=3.0)


@pytest.fixture
def schlagworte(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SchlagwortResolver:
    tags = tmp_path / "global_tags.yaml"
    tags.write_text(
        "tags:\n"
        "  - id: Digitalisierung\n"
        "    description: Digitale Infrastruktur\n"
        "  - id: Wohnungsbau\n"
        "    description: Sozialer Wohnungsbau\n",
        encoding="utf-8",
    )
    sachgebiete = tmp_path / "sachgebiete.yaml"
    sachgebiete.write_text(
        "tags:\n"
        "  - id: Umwelt\n"
        "    number: 100\n"
        "    description: Umweltschutz\n"
        "  - id: Bildung\n"
        "    number: 200\n"
        "    description: Bildungswesen\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(schlagworte_mod, "_GLOBAL_TAGS_FILES", [tags])
    monkeypatch.setattr(schlagworte_mod, "_SACHGEBIETE_FILES", [sachgebiete])
    return SchlagwortResolver()


# --- Helpers ------------------------------------------------------------------------


def _points(reader: InMemoryMetricReader, name: str) -> dict[frozenset, Any]:
    """Map each attribute set to its value (sum, or (count, sum) for histograms)."""
    data = reader.get_metrics_data()
    result: dict[frozenset, Any] = {}
    if data is None:
        return result
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name != name:
                    continue
                for point in metric.data.data_points:
                    key = frozenset((point.attributes or {}).items())
                    if isinstance(point, HistogramDataPoint):
                        result[key] = (point.count, point.sum)
                    else:
                        assert isinstance(point, NumberDataPoint)
                        result[key] = point.value
    return result


def _outcomes(reader: InMemoryMetricReader, resolver: str) -> dict[str, int]:
    """Resolution counts of one resolver, keyed by outcome."""
    result: dict[str, int] = {}
    for key, value in _points(reader, METRIC_NORMALIZATION_RESOLUTIONS).items():
        attributes = dict(key)
        if attributes[NORMALIZATION_RESOLVER] == resolver:
            result[str(attributes[NORMALIZATION_OUTCOME])] = value
    return result


def _by_resolver(reader: InMemoryMetricReader, name: str) -> dict[str, Any]:
    return {
        str(dict(key)[NORMALIZATION_RESOLVER]): value
        for key, value in _points(reader, name).items()
    }


# --- AuthorResolver -----------------------------------------------------------------


def test_author_batch_counts_each_outcome(
    reader: InMemoryMetricReader, authors: AuthorResolver
) -> None:
    authors.resolve_batch(["Olaf Scholz", "Olaf Scholzz", "Xaver Unbekannt", ""])

    assert _outcomes(reader, "author") == {"exact": 1, "fuzzy": 1, "unresolved": 2}
    count, total = _by_resolver(reader, METRIC_NORMALIZATION_MATCH_SCORE)["author"]
    assert count == 1
    assert 90.0 <= total < 100.0


def test_author_canonicalize_strict_counts_once(
    reader: InMemoryMetricReader, authors: AuthorResolver
) -> None:
    authors.canonicalize_authors(["Olaf Scholz", "Xaver Unbekannt"], strict=True)
    authors.canonicalize_author("Niemand Sonst", strict=True)

    # canonicalize_* go through resolve_batch: resolutions are not doubled.
    assert _outcomes(reader, "author") == {"exact": 1, "unresolved": 2}
    assert _by_resolver(reader, METRIC_NORMALIZATION_DROPPED) == {"author": 2}


def test_author_non_strict_drops_nothing(
    reader: InMemoryMetricReader, authors: AuthorResolver
) -> None:
    authors.canonicalize_authors(["Xaver Unbekannt"])
    authors.canonicalize_author("Niemand Sonst")

    assert _points(reader, METRIC_NORMALIZATION_DROPPED) == {}


def test_author_near_tie_counted(
    reader: InMemoryMetricReader, authors: AuthorResolver
) -> None:
    # "Anni" is equally close to "Anna" and "Anne".
    authors.resolve("Anni Schmidt")

    assert _by_resolver(reader, METRIC_NORMALIZATION_NEAR_TIES) == {"author": 1}


def test_author_empty_batch_records_nothing(
    reader: InMemoryMetricReader, authors: AuthorResolver
) -> None:
    authors.resolve_batch([])

    assert _points(reader, METRIC_NORMALIZATION_RESOLUTIONS) == {}


# --- OrganizationResolver -----------------------------------------------------------


def test_organization_batch_counts_each_outcome(
    reader: InMemoryMetricReader, organizations: OrganizationResolver
) -> None:
    organizations.resolve_batch(
        [
            "Sozialdemokratische Partei Deutschlands",
            "Sozialdemokratische Partei Deutschland",
            "Freie Wähler",
            "",
        ]
    )

    assert _outcomes(reader, "organization") == {
        "exact": 1,
        "fuzzy": 1,
        "unresolved": 2,
    }
    scores = _by_resolver(reader, METRIC_NORMALIZATION_MATCH_SCORE)
    assert scores["organization"][0] == 1


def test_organization_near_tie_counted(
    reader: InMemoryMetricReader, organizations: OrganizationResolver
) -> None:
    organizations.resolve("Ausschuss für Umwelt I")

    assert _by_resolver(reader, METRIC_NORMALIZATION_NEAR_TIES) == {"organization": 1}


def test_organization_canonicalize_strict_counts_dropped(
    reader: InMemoryMetricReader, organizations: OrganizationResolver
) -> None:
    organizations.canonicalize_organizations(
        ["Sozialdemokratische Partei Deutschlands", "Freie Wähler"], strict=True
    )
    organizations.canonicalize_organization("Piratenpartei", strict=True)

    assert _by_resolver(reader, METRIC_NORMALIZATION_DROPPED) == {"organization": 2}
    assert _outcomes(reader, "organization")["unresolved"] == 2


# --- SchlagwortResolver -------------------------------------------------------------


def test_tags_count_each_outcome(
    reader: InMemoryMetricReader, schlagworte: SchlagwortResolver
) -> None:
    schlagworte.canonicalise_tags(["Digitalisierung", "Digitalisirung", "Raumfahrt"])

    assert _outcomes(reader, "schlagwort") == {
        "exact": 1,
        "fuzzy": 1,
        "unresolved": 1,
    }
    assert _points(reader, METRIC_NORMALIZATION_DROPPED) == {}


def test_tags_strict_counts_dropped(
    reader: InMemoryMetricReader, schlagworte: SchlagwortResolver
) -> None:
    schlagworte.canonicalise_tags(["Digitalisierung", "Raumfahrt"], strict=True)

    assert _outcomes(reader, "schlagwort") == {"exact": 1, "unresolved": 1}
    assert _by_resolver(reader, METRIC_NORMALIZATION_DROPPED) == {"schlagwort": 1}


def test_single_tag_counted_once(
    reader: InMemoryMetricReader, schlagworte: SchlagwortResolver
) -> None:
    schlagworte.canonicalise_tag("Raumfahrt", strict=True)

    assert _outcomes(reader, "schlagwort") == {"unresolved": 1}
    assert _by_resolver(reader, METRIC_NORMALIZATION_DROPPED) == {"schlagwort": 1}


def test_sachgebiete_always_count_dropped(
    reader: InMemoryMetricReader, schlagworte: SchlagwortResolver
) -> None:
    schlagworte.canonicalise_sachgebiete(["Umwelt", "Raumfahrt"])

    assert _outcomes(reader, "sachgebiet") == {"exact": 1, "unresolved": 1}
    assert _by_resolver(reader, METRIC_NORMALIZATION_DROPPED) == {"sachgebiet": 1}


def test_checks_and_vocabulary_loading_record_nothing(
    reader: InMemoryMetricReader, schlagworte: SchlagwortResolver
) -> None:
    schlagworte.fuzzy_check_tag("Digitalisirung")

    assert _points(reader, METRIC_NORMALIZATION_RESOLUTIONS) == {}
    assert _points(reader, METRIC_NORMALIZATION_MATCH_SCORE) == {}


# --- Without OpenTelemetry ----------------------------------------------------------


def test_resolvers_work_with_metrics_disabled(
    monkeypatch: pytest.MonkeyPatch,
    authors: AuthorResolver,
    organizations: OrganizationResolver,
    schlagworte: SchlagwortResolver,
) -> None:
    monkeypatch.setattr(_metrics, "_INSTRUMENTS", None)

    assert authors.canonicalize_authors(["Xaver Unbekannt"], strict=True) == [None]
    assert organizations.canonicalize_organizations(["Freie Wähler"], strict=True) == []
    assert schlagworte.canonicalise_sachgebiete(["Raumfahrt"]) == []
