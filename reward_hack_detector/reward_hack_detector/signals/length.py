"""Length-based signals."""

from __future__ import annotations

import math
import re
from typing import Sequence

_WORD = re.compile(r"\w+", re.UNICODE)


def char_length(text: str) -> int:
    return len(text or "")


def token_length(text: str) -> int:
    return len(_WORD.findall(text or ""))


def length_zscore(value: int, population: Sequence[int]) -> float:
    """Z-score of ``value`` against ``population``.

    Returns 0.0 when the population has fewer than two distinct values
    (no signal to be extracted).
    """

    if not population:
        return 0.0
    n = len(population)
    mean = sum(population) / n
    if n < 2:
        return 0.0
    var = sum((x - mean) ** 2 for x in population) / (n - 1)
    std = math.sqrt(var)
    if std == 0.0:
        return 0.0
    return (value - mean) / std
