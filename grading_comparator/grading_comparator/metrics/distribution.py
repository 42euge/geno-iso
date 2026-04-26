"""Score distribution summaries: mean, std, quantiles, histogram."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True)
class ScoreSummary:
    n: int
    mean: float
    std: float
    minimum: float
    maximum: float
    q25: float
    median: float
    q75: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _quantile(sorted_vals: Sequence[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def describe(values: Sequence[float]) -> ScoreSummary:
    n = len(values)
    if n == 0:
        nan = float("nan")
        return ScoreSummary(0, nan, nan, nan, nan, nan, nan, nan)
    mean = sum(values) / n
    if n > 1:
        var = sum((v - mean) ** 2 for v in values) / (n - 1)
        std = math.sqrt(var)
    else:
        std = 0.0
    s = sorted(values)
    return ScoreSummary(
        n=n,
        mean=mean,
        std=std,
        minimum=s[0],
        maximum=s[-1],
        q25=_quantile(s, 0.25),
        median=_quantile(s, 0.5),
        q75=_quantile(s, 0.75),
    )
