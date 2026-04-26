"""Rank utilities: average-rank handling of ties (a la scipy 'average')."""
from __future__ import annotations

from typing import Sequence


def rankdata(values: Sequence[float]) -> list[float]:
    """Return average-tie ranks, 1-indexed.

    Equivalent to scipy.stats.rankdata(values, method='average').
    """
    n = len(values)
    if n == 0:
        return []
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-indexed average
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1
    return ranks
