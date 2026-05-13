"""Stress-test ``SchlagwortResolver.canonicalise_tags`` with a long list of
sachgebiet-derived inputs.

Reads all Sachgebiet IDs from
``pazufa_corelib/normalization/mappings/sachgebiete.yaml`` (via the resolver's
own loader) and builds a test list where:

 - 40% are exact (clean) hits
 - 50% contain small errors (wrong case, whitespace, trailing punctuation,
   doubled / dropped / transposed letters, umlaut transliterations)
 - 10% contain big errors (severe truncation, string reversal, full character
   scramble, or completely unknown noise)

Each input is fed through ``canonicalise_tags`` in both strict and non-strict
mode. The script prints per-bucket hit/miss statistics and a sampled
comparison table.

Run with:
    poetry run python tools/canonicalise_tags_sachgebiete_test.py
"""

from __future__ import annotations

import random
from collections.abc import Callable

from pazufa_corelib.normalization.schlagworte import (
    _SACHGEBIETE_FILES,
    SchlagwortResolver,
)
from pazufa_corelib.schlagworte_model import SachgebietFile

Perturbation = Callable[[str], str]

SEED = 20260416
TOTAL_CASES = 1000
SMALL_ERROR_PCT = 0.50
BIG_ERROR_PCT = 0.10
# Remainder (40%) is clean.

SAMPLE_PER_BUCKET = 10


# =====================================================================
# Small-error perturbations — close enough to the original that the
# resolver's 90.0 token_sort_ratio cutoff should usually still match.
# =====================================================================


def _lowercase(s: str) -> str:
    return s.lower()


def _uppercase(s: str) -> str:
    return s.upper()


def _pad_whitespace(s: str) -> str:
    return f"  {s}  "


def _tab_newline(s: str) -> str:
    return f"\t{s}\n"


def _add_period(s: str) -> str:
    return f"{s}."


def _add_bang(s: str) -> str:
    return f"{s}!"


def _double_letter(s: str) -> str:
    """Double the last alphabetic character."""
    for i in range(len(s) - 1, -1, -1):
        if s[i].isalpha():
            return s[: i + 1] + s[i] + s[i + 1 :]
    return s


def _drop_letter(s: str) -> str:
    """Drop an alphabetic character roughly in the middle of the string."""
    for i in range(len(s) // 2, len(s)):
        if s[i].isalpha():
            return s[:i] + s[i + 1 :]
    return s


def _swap_adjacent(s: str) -> str:
    """Swap two adjacent alphabetic characters near the middle."""
    mid = len(s) // 2
    for i in range(mid, len(s) - 1):
        if s[i].isalpha() and s[i + 1].isalpha():
            return s[:i] + s[i + 1] + s[i] + s[i + 2 :]
    return s


def _transliterate_umlauts(s: str) -> str:
    table = str.maketrans(
        {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "Ä": "Ae",
            "Ö": "Oe",
            "Ü": "Ue",
            "ß": "ss",
        }
    )
    return s.translate(table)


SMALL_ERRORS: list[Perturbation] = [
    _lowercase,
    _uppercase,
    _pad_whitespace,
    _tab_newline,
    _add_period,
    _add_bang,
    _double_letter,
    _drop_letter,
    _swap_adjacent,
    _transliterate_umlauts,
]


# =====================================================================
# Big-error perturbations — expected to miss the cutoff.
# =====================================================================


def _truncate_tiny(s: str) -> str:
    """Keep only the first three characters."""
    return s[:3]


def _reverse(s: str) -> str:
    return s[::-1]


_BIG_NOISE = [
    "Quantenphysik",
    "FooBarBaz",
    "AsdfQwerty",
    "Lorem ipsum",
    "xyzzy plugh",
    "1234567",
    "!@#$%^",
    "definitely not a sachgebiet",
]


def _make_big_errors(rng: random.Random) -> list[Perturbation]:
    def _scramble(s: str) -> str:
        chars = list(s)
        rng.shuffle(chars)
        return "".join(chars)

    def _replace_with_noise(_s: str) -> str:
        return rng.choice(_BIG_NOISE)

    return [_truncate_tiny, _reverse, _scramble, _replace_with_noise]


# =====================================================================
# Test-list construction
# =====================================================================


def load_sachgebiet_ids() -> list[str]:
    """Load all Sachgebiet IDs from ``SACHGEBIETE_FILES``."""
    ids: list[str] = []
    for path in _SACHGEBIETE_FILES:
        ids.extend(s.id for s in SachgebietFile.from_path(path).tags)
    return ids


def build_test_list(
    canonical_ids: list[str],
    total: int,
    small_error_pct: float,
    big_error_pct: float,
    seed: int,
) -> list[tuple[str, str | None, str]]:
    """Return a list of ``(raw_input, expected_canonical_or_None, bucket)``.

    ``expected_canonical`` is the original sachgebiet ID for clean and
    small-error inputs, and ``None`` for big-error inputs (where the
    expectation is a miss).
    """
    rng = random.Random(seed)
    n_small = int(round(total * small_error_pct))
    n_big = int(round(total * big_error_pct))
    n_clean = total - n_small - n_big
    big_errors = _make_big_errors(rng)

    result: list[tuple[str, str | None, str]] = []
    for _ in range(n_clean):
        original = rng.choice(canonical_ids)
        result.append((original, original, "clean"))
    for _ in range(n_small):
        original = rng.choice(canonical_ids)
        perturb = rng.choice(SMALL_ERRORS)
        result.append((perturb(original), original, "small"))
    for _ in range(n_big):
        original = rng.choice(canonical_ids)
        perturb = rng.choice(big_errors)
        result.append((perturb(original), None, "big"))

    rng.shuffle(result)
    return result


# =====================================================================
# Reporting
# =====================================================================


def _truncate(s: str, width: int) -> str:
    if len(s) <= width:
        return s
    return s[: max(0, width - 1)] + "…"


def _classify(expected: str | None, raw: str, resolved: str) -> str:
    """Categorise a single result.

    Returns one of: ``"correct"``, ``"miss"``, ``"wrong_match"``.

    In non-strict mode, a missed resolution returns the raw input unchanged,
    so ``resolved == raw`` (and ``resolved`` is not a known canonical id) means
    "miss". For big-error cases, ``expected`` is ``None``; a miss there is the
    desired outcome.
    """
    if expected is not None and resolved == expected:
        return "correct"
    if resolved == raw:
        return "miss"
    return "wrong_match"


def run() -> None:
    canonical_ids = load_sachgebiet_ids()
    cases = build_test_list(
        canonical_ids, TOTAL_CASES, SMALL_ERROR_PCT, BIG_ERROR_PCT, SEED
    )

    resolver = SchlagwortResolver()
    raw_inputs = [c[0] for c in cases]
    non_strict = resolver.canonicalise_tags(raw_inputs, strict=False)
    strict_result = resolver.canonicalise_tags(raw_inputs, strict=True)

    buckets: dict[str, dict[str, int]] = {
        name: {"total": 0, "correct": 0, "miss": 0, "wrong_match": 0}
        for name in ("clean", "small", "big")
    }
    for (raw, expected, bucket), resolved in zip(cases, non_strict):
        outcome = _classify(expected, raw, resolved)
        buckets[bucket]["total"] += 1
        buckets[bucket][outcome] += 1

    print(f"Vocabulary size       : {len(resolver._tag_ids_list)} tags")
    print(f"Sachgebiet IDs loaded : {len(canonical_ids)}")
    print(f"Test cases            : {len(cases)}")
    print(f"Non-strict out length : {len(non_strict)}")
    print(f"Strict out length     : {len(strict_result)}")
    print()

    header = (
        f"{'BUCKET':<8} {'TOTAL':>6} {'CORRECT':>8} {'MISS':>6} {'WRONG_MATCH':>12}"
    )
    print(header)
    print("-" * len(header))
    for name, stats in buckets.items():
        print(
            f"{name:<8} {stats['total']:>6} {stats['correct']:>8} "
            f"{stats['miss']:>6} {stats['wrong_match']:>12}"
        )
    print()

    by_bucket: dict[str, list[tuple[str, str | None, str]]] = {
        "clean": [],
        "small": [],
        "big": [],
    }
    for (raw, expected, bucket), resolved in zip(cases, non_strict):
        by_bucket[bucket].append((raw, expected, resolved))

    print(f"Sample (up to {SAMPLE_PER_BUCKET} per bucket):")
    tbl_header = f"{'BUCKET':<7} {'INPUT':<34} {'EXPECTED':<32} {'RESOLVED':<32} OK"
    print(tbl_header)
    print("-" * len(tbl_header))
    for name in ("clean", "small", "big"):
        for raw, expected, resolved in by_bucket[name][:SAMPLE_PER_BUCKET]:
            exp_display = expected if expected is not None else "(no match)"
            if expected is not None:
                ok = "✓" if resolved == expected else "✗"
            else:
                ok = "✓" if resolved == raw else "✗"
            raw_disp = _truncate(repr(raw), 34)
            exp_disp = _truncate(exp_display, 32)
            res_disp = _truncate(repr(resolved), 32)
            print(f"{name:<7} {raw_disp:<34} {exp_disp:<32} {res_disp:<32} {ok}")
        print()

    survivors = len(strict_result)
    print(f"Strict output ({survivors} of {len(cases)} survived).")
    print("First 20 strict resolutions:")
    print(strict_result[:20])


if __name__ == "__main__":
    run()
