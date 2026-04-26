"""Heuristic graders: cheap, deterministic functions over sample payloads."""
from __future__ import annotations

from typing import Callable, Mapping

from .base import Grader, GraderResult, Sample
from .precomputed import PrecomputedGrader


class HeuristicFileGrader(PrecomputedGrader):
    """Heuristic scores loaded from a precomputed file."""

    kind = "heuristic"


class CallableHeuristicGrader(Grader):
    """Wrap an arbitrary ``payload -> float`` callable as a grader."""

    kind = "heuristic"

    def __init__(
        self, name: str, fn: Callable[[Mapping[str, object]], float]
    ) -> None:
        super().__init__(name)
        self.fn = fn

    def score(self, sample: Sample) -> GraderResult:
        return GraderResult(
            grader=self.name,
            sample_id=sample.sample_id,
            score=float(self.fn(sample.payload)),
        )


def length_heuristic(field: str = "response") -> Callable[[Mapping[str, object]], float]:
    """Return a heuristic that scores by the length of ``payload[field]``."""

    def _score(payload: Mapping[str, object]) -> float:
        value = payload.get(field, "")
        return float(len(str(value)))

    return _score
