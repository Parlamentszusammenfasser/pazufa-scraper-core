"""Guardrail tests binding api_model.Sachgebiet to the shipped vocabulary.

`api_model.Sachgebiet` is handcrafted: the generated mirror only carries
`integer_<value>` members, so the readable names live here instead. That makes
the enum a second copy of a value set whose source of truth is
`normalization/mappings/sachgebiete.yaml`, and nothing else in the suite would
notice the two drifting apart.

These tests fail loudly when they do. The rest of the suite monkeypatches
`_SACHGEBIETE_FILES` to fixtures, so this module is also the only place the
*real* shipped YAML gets parsed and validated.
"""

from pathlib import Path

from pazufa_corelib.api_model import Sachgebiet
from pazufa_corelib.normalization.schlagworte import _SACHGEBIETE_FILES
from pazufa_corelib.schlagworte_model import (
    RESERVED_SCHLAGWORT_IDS,
    SachgebietFile,
)

# =====================================================================
# Helpers
# =====================================================================


def _vocabulary() -> dict[int, str]:
    """Load `number -> id` from every shipped Sachgebiet YAML file."""
    entries: dict[int, str] = {}
    for path in _SACHGEBIETE_FILES:
        for tag in SachgebietFile.from_path(Path(path)).tags:
            entries[tag.number] = tag.id
    return entries


def _member_name(sachgebiet_id: str) -> str:
    """Derive the enum member name from a vocabulary ID.

    Topic IDs are restricted to letters, spaces and hyphens by
    `BaseSchlagwort.validate_id_format`; the reserved IDs exempted from that
    rule add `@`. Each separator maps to one `_` — rather than collapsing runs
    — so `Katastrophen- und Zivilschutz` keeps its double underscore, matching
    how the generated mirror spells `Landes__Stadtentwicklung`.

    The result is a valid and, per `test_member_names_are_unique`, unique
    Python identifier.
    """
    for separator in (" ", "-", "@"):
        sachgebiet_id = sachgebiet_id.replace(separator, "_")
    return sachgebiet_id


# =====================================================================
# Guardrails
# =====================================================================


def test_vocabulary_file_is_valid() -> None:
    """The shipped YAML parses and validates; fixtures hide this elsewhere."""
    vocabulary = _vocabulary()

    assert vocabulary, "no Sachgebiet entries loaded from the shipped mappings"


def test_values_match_vocabulary_numbers() -> None:
    """Every enum value has a vocabulary entry, and vice versa."""
    enum_numbers = {member.value for member in Sachgebiet}
    yaml_numbers = set(_vocabulary())

    assert enum_numbers == yaml_numbers, (
        f"missing from the enum: {sorted(yaml_numbers - enum_numbers)}; "
        f"missing from sachgebiete.yaml: {sorted(enum_numbers - yaml_numbers)}"
    )


def test_names_match_vocabulary_ids() -> None:
    """Member names are the vocabulary IDs, with separators normalised."""
    actual = {member.value: member.name for member in Sachgebiet}
    expected = {
        number: _member_name(sachgebiet_id)
        for number, sachgebiet_id in _vocabulary().items()
    }

    mismatched = {
        number: (actual[number], expected[number])
        for number in actual.keys() & expected.keys()
        if actual[number] != expected[number]
    }

    assert not mismatched, f"enum name != vocabulary ID for {mismatched}"


def test_member_names_are_unique() -> None:
    """Two IDs must not normalise onto one identifier.

    `Enum` would silently alias the second onto the first rather than raise, so
    `test_names_match_vocabulary_ids` alone would not catch it.
    """
    names = [_member_name(sachgebiet_id) for sachgebiet_id in _vocabulary().values()]

    assert len(names) == len(set(names)), (
        f"vocabulary IDs collide as identifiers: "
        f"{sorted({name for name in names if names.count(name) > 1})}"
    )


def test_members_are_not_aliased() -> None:
    """No two entries share a number, which `Enum` would collapse into an alias."""
    assert len(Sachgebiet.__members__) == len(list(Sachgebiet))


def test_reserved_catch_alls_are_present() -> None:
    """`9900`/`9999` carry no topic but must stay addressable by name."""
    assert Sachgebiet.Unbekannt == 9900
    assert Sachgebiet.ohne__Systematik == 9999


def test_reserved_catch_alls_are_in_the_vocabulary() -> None:
    """The exemption in `validate_id_format` must keep them loadable.

    `ohne@-Systematik` cannot satisfy the topic-ID format rule, and before
    `RESERVED_SCHLAGWORT_IDS` existed both entries were simply absent from the
    YAML — leaving the vocabulary two short of the spec's value set.
    """
    vocabulary = _vocabulary()

    assert vocabulary[9900] == "Unbekannt"
    assert vocabulary[9999] == "ohne@-Systematik"
    assert RESERVED_SCHLAGWORT_IDS <= set(vocabulary.values())


def test_serialises_as_plain_int() -> None:
    """Naming the members must not change the wire representation."""
    assert Sachgebiet.Wahlen == 1080
    assert Sachgebiet(1080) is Sachgebiet.Wahlen
