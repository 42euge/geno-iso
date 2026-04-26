"""Bias analysis between graders.

The simplest grader-vs-grader bias signal is the systematic offset:
does grader A consistently score higher than grader B? We expose
``mean_difference`` plus a richer ``bias_report`` that also slices by
sample groups when the dataset carries categorical metadata.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class BiasSlice:
    group: str
    n: int
    mean_diff: float
    std_diff: float


def mean_difference(x: Sequence[float], y: Sequence[float]) -> float:
    """Mean of (x - y); positive => x scores systematically higher."""
    if len(x) != len(y):
        raise ValueError("length mismatch")
    if not x:
        return float("nan")
    return sum(a - b for a, b in zip(x, y)) / len(x)


def _stats(diffs: Sequence[float]) -> tuple[float, float]:
    n = len(diffs)
    if n == 0:
        return float("nan"), float("nan")
    mean = sum(diffs) / n
    if n < 2:
        return mean, 0.0
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    return mean, math.sqrt(var)


def bias_report(
    x: Sequence[float],
    y: Sequence[float],
    groups: Sequence[object] | None = None,
) -> dict[str, object]:
    """Compute overall and per-group mean / std of (x - y).

    ``groups`` should be a parallel sequence assigning each sample to a
    categorical bucket (e.g. domain or model family). When omitted only
    the overall slice is returned.
    """
    if len(x) != len(y):
        raise ValueError("length mismatch")
    diffs = [a - b for a, b in zip(x, y)]
    overall_mean, overall_std = _stats(diffs)
    report: dict[str, object] = {
        "overall": BiasSlice("__all__", len(diffs), overall_mean, overall_std),
    }
    if groups is None:
        return report
    if len(groups) != len(x):
        raise ValueError("groups length mismatch")
    buckets: dict[object, list[float]] = {}
    for d, g in zip(diffs, groups):
        buckets.setdefault(g, []).append(d)
    slices: list[BiasSlice] = []
    for g, ds in buckets.items():
        m, s = _stats(ds)
        slices.append(BiasSlice(str(g), len(ds), m, s))
    slices.sort(key=lambda b: -abs(b.mean_diff))
    report["by_group"] = slices
    return report
