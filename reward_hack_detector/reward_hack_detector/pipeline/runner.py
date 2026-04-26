"""End-to-end orchestration: build context, run detectors, score, rank, cluster."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from reward_hack_detector.analysis.clustering import (
    Cluster,
    cluster_high_reward_low_quality,
)
from reward_hack_detector.analysis.correlation import reward_length_correlation
from reward_hack_detector.analysis.ranking import sort_by_suspicion, top_k
from reward_hack_detector.analysis.scoring import SuspicionScore, score_sample
from reward_hack_detector.data import Sample
from reward_hack_detector.detectors import default_detectors
from reward_hack_detector.detectors.base import (
    AnalysisContext,
    Detector,
    DetectorResult,
)
from reward_hack_detector.signals.embedding import EmbeddingSignal
from reward_hack_detector.signals.length import char_length, token_length


@dataclass
class PipelineResult:
    samples: list[Sample]
    scores: list[SuspicionScore]
    context: AnalysisContext
    clusters: list[Cluster] = field(default_factory=list)
    embedding_backend: str = "bow"

    def top(self, k: int) -> list[SuspicionScore]:
        return top_k(self.scores, k)

    def hack_type_counts(self, threshold: float = 0.4) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.scores:
            for name, sc in s.detector_scores.items():
                if sc >= threshold:
                    counts[name] = counts.get(name, 0) + 1
        return counts

    def summary(self, top_n: int = 10) -> dict:
        ctx = self.context
        return {
            "n_samples": len(self.samples),
            "reward_mean": round(ctx.reward_mean, 4),
            "reward_std": round(ctx.reward_std, 4),
            "length_mean": round(ctx.length_mean, 4),
            "length_std": round(ctx.length_std, 4),
            "reward_length_correlation": round(ctx.reward_length_corr, 4),
            "embedding_backend": self.embedding_backend,
            "hack_type_counts": self.hack_type_counts(),
            "n_suspicious": sum(1 for s in self.scores if s.suspicion >= 0.5),
            "top_suspicions": [s.to_dict() for s in self.top(top_n)],
            "clusters": [c.to_dict() for c in self.clusters],
        }


def _basic_stats(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var)


def _build_context(
    samples: Sequence[Sample], embedding: Optional[EmbeddingSignal]
) -> AnalysisContext:
    rewards = [s.reward for s in samples]
    char_lens = [char_length(s.output) for s in samples]
    tok_lens = [token_length(s.output) for s in samples]
    rmean, rstd = _basic_stats(rewards)
    lmean, lstd = _basic_stats([float(x) for x in tok_lens])
    corr = reward_length_correlation(rewards, tok_lens)
    return AnalysisContext(
        rewards=list(rewards),
        char_lengths=char_lens,
        token_lengths=tok_lens,
        reward_mean=rmean,
        reward_std=rstd,
        length_mean=lmean,
        length_std=lstd,
        reward_length_corr=corr,
        embedding=embedding,
    )


def detect(
    samples: Iterable[Sample],
    *,
    detectors: Optional[Sequence[Detector]] = None,
    use_embeddings: bool = False,
    embedding_model: Optional[str] = None,
    tag_threshold: float = 0.4,
    cluster_min_suspicion: float = 0.4,
) -> PipelineResult:
    """Run the full detection pipeline over ``samples``.

    Parameters mirror the CLI flags but accept any ``Iterable[Sample]``.
    """

    samples = list(samples)
    if not samples:
        ctx = AnalysisContext(
            rewards=[],
            char_lengths=[],
            token_lengths=[],
            reward_mean=0.0,
            reward_std=0.0,
            length_mean=0.0,
            length_std=0.0,
            reward_length_corr=0.0,
            embedding=None,
        )
        return PipelineResult(samples=[], scores=[], context=ctx)

    embedding = None
    if use_embeddings or embedding_model:
        kwargs = {"use_model": True}
        if embedding_model:
            kwargs["model_name"] = embedding_model
        embedding = EmbeddingSignal(**kwargs)
    elif any(s.reference for s in samples):
        # Always have a fallback for reference comparisons.
        embedding = EmbeddingSignal(use_model=False)

    ctx = _build_context(samples, embedding)
    detector_list = list(detectors) if detectors is not None else default_detectors()

    scores: list[SuspicionScore] = []
    for sample in samples:
        results: list[DetectorResult] = [d.analyze(sample, ctx) for d in detector_list]
        scores.append(
            score_sample(
                sample,
                results,
                reward_mean=ctx.reward_mean,
                reward_std=ctx.reward_std,
                tag_threshold=tag_threshold,
            )
        )

    rewards_by_id = {s.id or f"sample_{i:04d}": s.reward for i, s in enumerate(samples)}
    clusters = cluster_high_reward_low_quality(
        scores,
        rewards_by_id,
        min_suspicion=cluster_min_suspicion,
        min_reward_z=0.0,
    )

    return PipelineResult(
        samples=samples,
        scores=sort_by_suspicion(scores),
        context=ctx,
        clusters=clusters,
        embedding_backend=embedding.backend if embedding is not None else "none",
    )
