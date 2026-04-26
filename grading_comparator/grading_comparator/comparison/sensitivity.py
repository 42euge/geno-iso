"""Selection sensitivity: how does the top-k change when we swap graders?"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class SelectionShift:
    grader_a: str
    grader_b: str
    k: int
    overlap: int
    jaccard: float
    only_a: list[str]
    only_b: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _top_k_ids(
    sample_ids: Sequence[str], values: Sequence[float], k: int
) -> list[str]:
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    return [sample_ids[i] for i in order[:k]]


def selection_sensitivity(
    sample_ids: Sequence[str],
    scores: Mapping[str, Sequence[float]],
    k: int,
) -> list[SelectionShift]:
    """For each grader pair, report how the top-k selection changes."""
    names = list(scores.keys())
    n = len(sample_ids)
    k = max(1, min(k, n))
    top_sets = {g: _top_k_ids(sample_ids, scores[g], k) for g in names}

    shifts: list[SelectionShift] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            sa = set(top_sets[a])
            sb = set(top_sets[b])
            inter = sa & sb
            union = sa | sb
            jaccard = len(inter) / len(union) if union else float("nan")
            shifts.append(
                SelectionShift(
                    grader_a=a,
                    grader_b=b,
                    k=k,
                    overlap=len(inter),
                    jaccard=jaccard,
                    only_a=sorted(sa - sb),
                    only_b=sorted(sb - sa),
                )
            )
    return shifts
