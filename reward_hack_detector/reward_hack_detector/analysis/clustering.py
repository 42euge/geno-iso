"""Lightweight clustering of high-reward, low-quality outputs.

This is intentionally simple — the goal is to surface a handful of
recognisable failure modes, not to do precise unsupervised learning.
We project each suspicious sample onto the unit hypercube of detector
scores plus reward and group nearby points with single-link grouping.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Sequence

from reward_hack_detector.analysis.scoring import SuspicionScore


@dataclass
class Cluster:
    cluster_id: int
    members: list[str] = field(default_factory=list)  # sample ids
    avg_suspicion: float = 0.0
    avg_reward: float = 0.0
    dominant_hack: str = "mixed"
    detector_means: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "size": len(self.members),
            "members": list(self.members),
            "avg_suspicion": round(self.avg_suspicion, 4),
            "avg_reward": round(self.avg_reward, 4),
            "dominant_hack": self.dominant_hack,
            "detector_means": {
                k: round(v, 4) for k, v in self.detector_means.items()
            },
        }


def _vector(score: SuspicionScore, detector_names: Sequence[str]) -> list[float]:
    return [score.detector_scores.get(name, 0.0) for name in detector_names]


def _euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def cluster_high_reward_low_quality(
    scores: Sequence[SuspicionScore],
    rewards: dict[str, float],
    *,
    min_suspicion: float = 0.4,
    min_reward_z: float = 0.0,
    radius: float = 0.35,
) -> list[Cluster]:
    """Group suspicious + high-reward samples by detector-pattern similarity.

    Single-link agglomerative grouping: any two points within ``radius``
    in detector-score space land in the same cluster.
    """

    candidates = [
        s
        for s in scores
        if s.suspicion >= min_suspicion and s.reward_z >= min_reward_z
    ]
    if not candidates:
        return []

    detector_names = sorted(
        {name for s in scores for name in s.detector_scores.keys()}
    )
    vectors = [_vector(s, detector_names) for s in candidates]

    # Union-find by single-link threshold.
    parent = list(range(len(candidates)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            if _euclidean(vectors[i], vectors[j]) <= radius:
                union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(candidates)):
        groups[find(i)].append(i)

    clusters: list[Cluster] = []
    for cid, indices in enumerate(
        sorted(groups.values(), key=lambda g: -len(g)), start=1
    ):
        members = [candidates[i] for i in indices]
        member_ids = [m.sample_id for m in members]
        member_rewards = [rewards.get(m.sample_id, 0.0) for m in members]
        avg_reward = sum(member_rewards) / len(member_rewards)
        avg_suspicion = sum(m.suspicion for m in members) / len(members)
        hack_counts: Counter[str] = Counter(m.primary_hack for m in members)
        dominant = hack_counts.most_common(1)[0][0] if hack_counts else "mixed"
        detector_means = {
            name: sum(m.detector_scores.get(name, 0.0) for m in members)
            / len(members)
            for name in detector_names
        }
        clusters.append(
            Cluster(
                cluster_id=cid,
                members=member_ids,
                avg_suspicion=avg_suspicion,
                avg_reward=avg_reward,
                dominant_hack=dominant,
                detector_means=detector_means,
            )
        )
    return clusters
