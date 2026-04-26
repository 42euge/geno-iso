"""Rubric schema definitions.

A rubric defines how a judge model (or rule-based scorer) grades a candidate
response. Three rubric kinds are supported:

  - scalar: single integer/float score in a fixed range
  - pairwise: judge picks A or B (or "tie") given two candidate responses
  - multi_criteria: vector of scalar scores across named criteria
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RubricKind(str, Enum):
    SCALAR = "scalar"
    PAIRWISE = "pairwise"
    MULTI_CRITERIA = "multi_criteria"


@dataclass
class Criterion:
    name: str
    description: str
    scale_min: int = 1
    scale_max: int = 5
    weight: float = 1.0


@dataclass
class _BaseRubric:
    name: str
    description: str
    judge_prompt_template: str
    kind: RubricKind = RubricKind.SCALAR
    version: str = "0.1.0"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScalarRubric(_BaseRubric):
    scale_min: int = 1
    scale_max: int = 5

    def __post_init__(self) -> None:
        self.kind = RubricKind.SCALAR
        if self.scale_min >= self.scale_max:
            raise ValueError(
                f"scalar rubric '{self.name}': scale_min ({self.scale_min}) "
                f"must be < scale_max ({self.scale_max})"
            )


@dataclass
class PairwiseRubric(_BaseRubric):
    allow_tie: bool = True
    labels: tuple[str, ...] = ("A", "B")

    def __post_init__(self) -> None:
        self.kind = RubricKind.PAIRWISE
        if len(self.labels) != 2:
            raise ValueError(
                f"pairwise rubric '{self.name}': exactly 2 labels required, got {self.labels}"
            )


@dataclass
class MultiCriteriaRubric(_BaseRubric):
    criteria: list[Criterion] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.kind = RubricKind.MULTI_CRITERIA
        if not self.criteria:
            raise ValueError(
                f"multi_criteria rubric '{self.name}': at least one criterion required"
            )
        seen = set()
        for c in self.criteria:
            if c.name in seen:
                raise ValueError(
                    f"multi_criteria rubric '{self.name}': duplicate criterion '{c.name}'"
                )
            seen.add(c.name)


Rubric = ScalarRubric | PairwiseRubric | MultiCriteriaRubric
