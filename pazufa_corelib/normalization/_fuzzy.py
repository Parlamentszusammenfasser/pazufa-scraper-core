"""Generic fuzzy string resolution shared across normalization resolvers.

Private module — import only from within the normalization package.
"""

import logging
from collections.abc import Callable
from typing import Any

import numpy as np
from rapidfuzz.process import cdist

LOGGER = logging.getLogger(__name__)


def fuzzy_resolve(
    raw: list[str],
    canonical: list[str],
    scorer: Any,
    processor: Callable[[str], str] | None,
    cutoff: float,
    strict: bool = False,
    near_tie_epsilon: float = 1.0,
) -> list[tuple[str, str, float]]:
    """Fuzzy-match raw strings against a canonical list.

    Args:
        raw: Strings to resolve.
        canonical: Accepted strings to match against.
        scorer: rapidfuzz scorer (e.g. ``fuzz.WRatio``, ``fuzz.token_sort_ratio``).
        processor: Normalization function applied to both sides before scoring.
        cutoff: Minimum score; matches below this threshold are treated as 0.0.
        strict: If ``True``, unmatched strings are dropped from the result.
            If ``False``, they are returned with score ``0.0`` and the resolved
            value set to the original string.
        near_tie_epsilon: Maximum score gap between the best and second-best
            match that triggers a near-tie warning log.

    Returns:
        List of ``(original, resolved, score)`` tuples in the same order as
        *raw*. Unmatched entries are omitted when ``strict=True``.

    Raises:
        ValueError: If *raw* or *canonical* is empty.
    """
    if not raw or not canonical:
        raise ValueError(
            f"raw and canonical must not be empty, "
            f"got {len(raw)} raw and {len(canonical)} canonical strings"
        )

    matrix = cdist(
        raw,
        canonical,
        scorer=scorer,
        processor=processor,
        score_cutoff=cutoff,
    )

    result: list[tuple[str, str, float]] = []

    for i, raw_str in enumerate(raw):
        row = matrix[i]
        order = np.argsort(row, kind="stable")[::-1]
        best_idx = int(order[0])
        best_score = float(row[best_idx])

        if best_score == 0.0:
            if not strict:
                result.append((raw_str, raw_str, 0.0))
            continue

        if len(order) >= 2:
            second_best_idx = int(order[1])
            second_best_score = float(row[second_best_idx])
            delta = best_score - second_best_score
            if second_best_score > 0 and delta <= near_tie_epsilon:
                LOGGER.warning(
                    "Near-tie in fuzzy_resolve",
                    extra={
                        "raw": raw_str,
                        "best_match": canonical[best_idx],
                        "best_score": best_score,
                        "second_match": canonical[second_best_idx],
                        "second_score": second_best_score,
                        "delta": delta,
                        "epsilon": near_tie_epsilon,
                    },
                )

        result.append((raw_str, canonical[best_idx], best_score))

    if not result:
        LOGGER.warning(
            "fuzzy_resolve returned 0 results",
            extra={"strict": strict, "raw_count": len(raw)},
        )

    return result
