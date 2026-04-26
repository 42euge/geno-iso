"""Base abstractions for grading methodologies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class Sample:
    """A single dataset item to be graded."""
    sample_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraderResult:
    """A single grader's score for one sample."""
    grader: str
    sample_id: str
    score: float
    metadata: Mapping[str, Any] = field(default_factory=dict)


class Grader(ABC):
    """Abstract grader. Concrete graders return a numeric score per sample.

    Subclasses implement ``score`` for one sample and inherit ``score_all``.
    They may override ``score_all`` for batched evaluation.
    """

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def score(self, sample: Sample) -> GraderResult:
        ...

    def score_all(self, samples: Iterable[Sample]) -> list[GraderResult]:
        return [self.score(s) for s in samples]

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r})"
