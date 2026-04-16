"""Smoke-test / demo for SchlagwortResolver.canonicalise_tags.
Feeds a long list of realistic but dirty tag inputs — typos, wrong casing,
extra whitespace, umlaut variants, partially-correct phrases, and completely
unknown noise — through ``canonicalise_tags`` in both strict and non-strict
mode and prints a comparison table.

Run with:
    poetry run python tools/canonicalise_tags_demo.py
"""

from __future__ import annotations

from collector_core.normalization.schlagworte import SchlagwortResolver

# Each entry: (raw input, expected canonical id or None if no match expected).
# The resolver's fuzzy cutoff is 90.0 on token_sort_ratio, so only fairly
# close variants should match. We mix clear hits, marginal cases, and misses.
TEST_CASES: list[tuple[str, str | None]] = [
    # --- exact hits from global_tags.yaml ---
    ("Digitalisierung", "Digitalisierung"),
    ("Wohnungsbau", "Wohnungsbau"),
    ("Energiewende", "Energiewende"),
    ("Pflegenotstand", "Pflegenotstand"),
    # --- exact hits from sachgebiete.yaml ---
    ("Umwelt", "Umwelt"),
    ("Bildung", "Bildung"),
    ("Gesundheit", "Gesundheit"),
    ("Verkehr", "Verkehr"),
    ("Klima", "Klima"),
    ("Landwirtschaft", "Landwirtschaft"),
    # --- wrong casing (normalised away by processor) ---
    ("digitalisierung", "Digitalisierung"),
    ("WOHNUNGSBAU", "Wohnungsbau"),
    ("energiewende", "Energiewende"),
    ("umwelt", "Umwelt"),
    ("BILDUNG", "Bildung"),
    # --- whitespace noise ---
    ("  Digitalisierung  ", "Digitalisierung"),
    ("\tUmwelt\n", "Umwelt"),
    # --- minor typos (should still clear the 90.0 cutoff) ---
    ("Digitalisirung", "Digitalisierung"),  # missing 'e'
    ("Wohnungsbauu", "Wohnungsbau"),  # doubled 'u'
    ("Energiewendee", "Energiewende"),  # doubled 'e'
    ("Pflegennotstand", "Pflegenotstand"),  # doubled 'n'
    # --- punctuation (stripped by processor) ---
    ("Umwelt.", "Umwelt"),
    ("Bildung!", "Bildung"),
    ("Klima?", "Klima"),
    # --- multi-word sachgebiete ---
    ("Staat und Politik", "Staat und Politik"),
    ("staat und politik", "Staat und Politik"),
    ("Innere Sicherheit", "Innere Sicherheit"),
    ("Arbeit und Beschäftigung", "Arbeit und Beschäftigung"),
    # --- heavy typos / partial forms — expected to MISS the cutoff ---
    ("Dgitalisierung", None),  # missing 'i' at position 1 — borderline
    ("Wohnung", None),  # substring only
    ("Energie", None),  # substring of Energiewende
    ("Bild", None),  # too short
    # --- completely unknown terms ---
    ("Quantenphysik", None),
    ("FooBarBaz", None),
    ("AsdfQwerty", None),
    ("Lorem ipsum", None),
    # --- empty-ish / weird inputs (but still valid strings) ---
    ("xyz", None),
    ("123 Mainstreet", None),
]


def _fmt_status(raw: str, expected: str | None, actual: str) -> str:
    """Return a ✓/✗ status string for a single case."""
    if expected is None:
        # non-strict mode returns raw unchanged on miss
        ok = actual == raw
        return "✓" if ok else "✗"
    return "✓" if actual == expected else "✗"


def run_demo() -> None:
    """Run the demo against a fresh resolver and print a comparison table."""
    resolver = SchlagwortResolver()
    raw_inputs = [case[0] for case in TEST_CASES]

    non_strict = resolver.canonicalise_tags(raw_inputs, strict=False)
    strict = resolver.canonicalise_tags(raw_inputs, strict=True)

    print(f"Vocabulary size: {len(resolver._tag_ids_list)} tags")
    print(f"Inputs:          {len(raw_inputs)}")
    print(
        f"Non-strict out:  {len(non_strict)} (unchanged length — misses returned as-is)"
    )
    print(f"Strict out:      {len(strict)} (misses dropped)")
    print()

    header = f"{'INPUT':<30} {'EXPECTED':<28} {'RESOLVED (non-strict)':<28} OK"
    print(header)
    print("-" * len(header))

    mismatches: list[tuple[str, str | None, str]] = []
    for (raw, expected), actual in zip(TEST_CASES, non_strict):
        status = _fmt_status(raw, expected, actual)
        exp_display = expected if expected is not None else "(no match)"
        print(f"{raw!r:<30} {exp_display:<28} {actual!r:<28} {status}")
        if status == "✗":
            mismatches.append((raw, expected, actual))

    print()
    print("=" * 80)
    print(f"Strict output ({len(strict)} survived):")
    print(strict)
    print()
    dropped = [
        raw
        for raw, canonical in zip(raw_inputs, non_strict)
        if raw == canonical and raw not in resolver._tag_ids_list
    ]
    print(f"Dropped by strict mode ({len(dropped)}): {dropped}")

    print()
    print("=" * 80)
    if mismatches:
        print(f"{len(mismatches)} mismatch(es):")
        for raw, expected, actual in mismatches:
            print(f"  {raw!r} — expected {expected!r}, got {actual!r}")
    else:
        print("All expectations met.")


if __name__ == "__main__":
    run_demo()
