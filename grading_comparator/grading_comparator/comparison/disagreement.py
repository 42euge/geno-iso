"""Identify samples on which graders disagree most strongly.

Disagreement is scored as the spread of standardised scores across
graders for each sample: each grader's vector is z-normalised so that
graders with different scales are commensurable, and the per-sample
range (max - min across graders) is used as the disagreement score.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class DisagreementSample:
    sample_id: str
    disagreement: float
    scores: dict[str, float]
    standardised: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _zscore(values: Sequence[float]) -> list[float]:
    n = len(values)
    if n == 0:
        return []
    mean = sum(values) / n
    if n < 2:
        return [0.0] * n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = math.sqrt(var)
    if std == 0:
        return [0.0] * n
    return [(v - mean) / std for v in values]


def top_disagreements(
    sample_ids: Sequence[str],
    scores: Mapping[str, Sequence[float]],
    limit: int = 20,
) -> list[DisagreementSample]:
    if not scores:
        return []
    grader_names = list(scores.keys())
    z_by_grader = {g: _zscore(list(scores[g])) for g in grader_names}

    rows: list[DisagreementSample] = []
    for idx, sid in enumerate(sample_ids):
        zs = [z_by_grader[g][idx] for g in grader_names]
        raw = {g: float(scores[g][idx]) for g in grader_names}
        std_map = {g: zs[i] for i, g in enumerate(grader_names)}
        rows.append(
            DisagreementSample(
                sample_id=sid,
                disagreement=max(zs) - min(zs) if zs else 0.0,
                scores=raw,
                standardised=std_map,
            )
        )

    rows.sort(key=lambda r: r.disagreement, reverse=True)
    return rows[:limit]
