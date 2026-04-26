"""Agreement metrics between two graders."""
from __future__ import annotations

import math
from typing import Sequence


def agreement_rate(
    x: Sequence[float],
    y: Sequence[float],
    tolerance: float = 0.0,
) -> float:
    """Fraction of pairs whose scores match within ``tolerance``."""
    if len(x) != len(y):
        raise ValueError("length mismatch")
    if not x:
        return float("nan")
    matches = sum(1 for a, b in zip(x, y) if abs(a - b) <= tolerance)
    return matches / len(x)


def binarised_agreement(
    x: Sequence[float],
    y: Sequence[float],
    threshold_x: float,
    threshold_y: float | None = None,
) -> float:
    """Fraction of pairs that agree on >= threshold (pass/fail style)."""
    if threshold_y is None:
        threshold_y = threshold_x
    if len(x) != len(y):
        raise ValueError("length mismatch")
    if not x:
        return float("nan")
    matches = sum(
        1
        for a, b in zip(x, y)
        if (a >= threshold_x) == (b >= threshold_y)
    )
    return matches / len(x)


def cohen_kappa(
    x: Sequence[float],
    y: Sequence[float],
    threshold_x: float,
    threshold_y: float | None = None,
) -> float:
    """Cohen's kappa over the pass/fail binarisation of x and y."""
    if threshold_y is None:
        threshold_y = threshold_x
    if len(x) != len(y):
        raise ValueError("length mismatch")
    n = len(x)
    if n == 0:
        return float("nan")
    bx = [a >= threshold_x for a in x]
    by = [b >= threshold_y for b in y]
    po = sum(1 for a, b in zip(bx, by) if a == b) / n
    px = sum(bx) / n
    py = sum(by) / n
    pe = px * py + (1 - px) * (1 - py)
    if math.isclose(pe, 1.0):
        return float("nan")
    return (po - pe) / (1 - pe)


def top_k_overlap(
    x: Sequence[float], y: Sequence[float], k: int
) -> float:
    """Jaccard-style overlap of the top-k indices under each grader.

    Useful as a "selection sensitivity" check: if the top-10% chosen by
    grader A barely overlaps with the top-10% chosen by grader B, the
    grading method has a large effect on selection.
    """
    if len(x) != len(y):
        raise ValueError("length mismatch")
    n = len(x)
    if n == 0 or k <= 0:
        return float("nan")
    k = min(k, n)
    top_x = set(sorted(range(n), key=lambda i: x[i], reverse=True)[:k])
    top_y = set(sorted(range(n), key=lambda i: y[i], reverse=True)[:k])
    inter = len(top_x & top_y)
    union = len(top_x | top_y)
    return inter / union if union else float("nan")
