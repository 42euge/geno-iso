"""Rubric-based graders.

Two flavours are provided:

* :class:`RubricFileGrader` — loads rubric scores from a precomputed file
  (the common case when rubrics are evaluated by an LLM out-of-band).
* :class:`WeightedRubricGrader` — a simple inline rubric: a set of named
  criteria with weights, applied to ``sample.payload``.
"""
from __future__ import annotations

from typing import Mapping

from .base import Grader, GraderResult, Sample
from .precomputed import PrecomputedGrader


class RubricFileGrader(PrecomputedGrader):
    """Rubric scores loaded from disk; identifies as a rubric grader."""

    kind = "rubric"


class WeightedRubricGrader(Grader):
    """Score = sum(weight_i * payload[criterion_i]).

    Useful for tests and for simple analytic rubrics where each criterion
    is already a numeric field on the sample.
    """

    kind = "rubric"

    def __init__(self, name: str, weights: Mapping[str, float]) -> None:
        super().__init__(name)
        if not weights:
            raise ValueError("WeightedRubricGrader requires at least one weight")
        self.weights = dict(weights)

    def score(self, sample: Sample) -> GraderResult:
        total = 0.0
        for criterion, weight in self.weights.items():
            if criterion not in sample.payload:
                raise KeyError(
                    f"sample {sample.sample_id!r} missing criterion "
                    f"{criterion!r} for rubric {self.name!r}"
                )
            total += weight * float(sample.payload[criterion])
        return GraderResult(
            grader=self.name, sample_id=sample.sample_id, score=total
        )
