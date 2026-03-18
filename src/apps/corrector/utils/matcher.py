from __future__ import annotations

from typing import TYPE_CHECKING

from rapidfuzz import process, fuzz

if TYPE_CHECKING:
    from apps.corrector.models import ReferenceProduct

DEFAULT_THRESHOLD = 70


def find_best_match(
    product_name: str,
    queryset,
) -> tuple["ReferenceProduct | None", float]:
    """Return the best-matching ReferenceProduct and its similarity score.

    Uses WRatio (weighted ratio) which handles partial matches, token order
    differences, and abbreviations better than simple ratio alone.

    Args:
        product_name: The raw product name string to match against the catalog.
        queryset: A QuerySet (or iterable) of ReferenceProduct instances.

    Returns:
        A 2-tuple of (ReferenceProduct | None, float).  The first element is
        None only when the queryset is empty; otherwise the best-scoring
        candidate is always returned together with its score (0.0–100.0).
        Use ``auto_confirm_threshold`` to decide whether the score is
        high enough to auto-confirm the suggestion.
    """
    products = list(queryset)
    if not products:
        return None, 0.0

    choices = {p.pk: p.product_name for p in products}

    result = process.extractOne(
        product_name,
        choices,
        scorer=fuzz.WRatio,
        score_cutoff=0,
    )

    if result is None:
        return None, 0.0

    _matched_name, score, matched_pk = result
    best_product = next(p for p in products if p.pk == matched_pk)
    return best_product, float(score)


def auto_confirm_threshold(score: float, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """Return True when a score is high enough to be auto-confirmed."""
    return score >= threshold
