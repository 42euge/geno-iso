"""Detector ABC + shared types."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional

from reward_hack_detector.data import Sample
from reward_hack_detector.signals.embedding import EmbeddingSignal


@dataclass
class AnalysisContext:
    """Dataset-level statistics shared across detectors."""

    rewards: list[float]
    char_lengths: list[int]
    token_lengths: list[int]
    reward_mean: float
    reward_std: float
    length_mean: float
    length_std: float
    reward_length_corr: float
    embedding: Optional[EmbeddingSignal] = None


@dataclass
class DetectorResult:
    """Output of a single detector for a single sample."""

    name: str
    score: float  # in [0, 1]; higher = more suspicious
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "reasons": list(self.reasons),
            "metrics": {k: round(v, 4) for k, v in self.metrics.items()},
        }


class Detector(abc.ABC):
    """Base class for detectors. Subclasses implement :meth:`analyze`."""

    name: str = "detector"
    hack_type: str = "generic"

    @abc.abstractmethod
    def analyze(self, sample: Sample, ctx: AnalysisContext) -> DetectorResult:
        """Score a single ``sample`` for this hack pattern."""


def clamp01(x: float) -> float:
    if x != x:  # NaN
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x
