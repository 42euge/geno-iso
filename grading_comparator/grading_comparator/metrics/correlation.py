"""Correlation coefficients implemented in pure Python.

Provides Pearson, Spearman (rank Pearson with average-tie ranks) and
Kendall's tau-b (with tie correction).
"""
from __future__ import annotations

import math
from typing import Sequence

from .ranking import rankdata


def _check_pair(x: Sequence[float], y: Sequence[float]) -> int:
    if len(x) != len(y):
        raise ValueError(f"length mismatch: {len(x)} vs {len(y)}")
    if len(x) < 2:
        raise ValueError("need at least 2 points for correlation")
    return len(x)


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson product-moment correlation."""
    n = _check_pair(x, y)
    mx = sum(x) / n
    my = sum(y) / n
    num = 0.0
    sx2 = 0.0
    sy2 = 0.0
    for xi, yi in zip(x, y):
        dx = xi - mx
        dy = yi - my
        num += dx * dy
        sx2 += dx * dx
        sy2 += dy * dy
    denom = math.sqrt(sx2 * sy2)
    if denom == 0.0:
        return float("nan")
    return num / denom


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman rank correlation (Pearson on average-tie ranks)."""
    _check_pair(x, y)
    rx = rankdata(x)
    ry = rankdata(y)
    return pearson(rx, ry)


def kendall_tau(x: Sequence[float], y: Sequence[float]) -> float:
    """Kendall's tau-b with tie correction.

    tau_b = (C - D) / sqrt((P - T_x) * (P - T_y))
    where P = n*(n-1)/2, C/D are concordant/discordant pair counts,
    and T_x, T_y are tie corrections in x and y respectively.
    Pairs tied in both x and y count toward neither C nor D nor T_x/T_y.
    """
    n = _check_pair(x, y)
    concordant = 0
    discordant = 0
    tx = 0
    ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
                continue
            if dy == 0:
                ty += 1
                continue
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                concordant += 1
            else:
                discordant += 1
    total_pairs = n * (n - 1) // 2
    denom = math.sqrt((total_pairs - tx) * (total_pairs - ty))
    if denom == 0.0:
        return float("nan")
    return (concordant - discordant) / denom
