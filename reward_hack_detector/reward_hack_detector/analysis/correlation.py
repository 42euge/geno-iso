"""Correlation utilities (stdlib-only)."""

from __future__ import annotations

import math
from typing import Sequence


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Sample Pearson correlation coefficient.

    Returns 0.0 when undefined (n < 2 or zero variance).
    """

    n = len(xs)
    if n != len(ys) or n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sx = sy = sxy = 0.0
    for x, y in zip(xs, ys):
        dx = x - mean_x
        dy = y - mean_y
        sx += dx * dx
        sy += dy * dy
        sxy += dx * dy
    if sx == 0.0 or sy == 0.0:
        return 0.0
    return sxy / math.sqrt(sx * sy)


def reward_length_correlation(
    rewards: Sequence[float], lengths: Sequence[int]
) -> float:
    return pearson(list(rewards), [float(x) for x in lengths])
