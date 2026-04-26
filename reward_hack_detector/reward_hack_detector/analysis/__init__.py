"""Aggregation and ranking of detector results into per-sample scores."""

from reward_hack_detector.analysis.correlation import (
    pearson,
    reward_length_correlation,
)
from reward_hack_detector.analysis.scoring import (
    SuspicionScore,
    score_sample,
)
from reward_hack_detector.analysis.ranking import top_k, sort_by_suspicion
from reward_hack_detector.analysis.clustering import (
    cluster_high_reward_low_quality,
    Cluster,
)

__all__ = [
    "pearson",
    "reward_length_correlation",
    "SuspicionScore",
    "score_sample",
    "top_k",
    "sort_by_suspicion",
    "cluster_high_reward_low_quality",
    "Cluster",
]
