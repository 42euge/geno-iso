"""Ranking helpers."""

from __future__ import annotations

from typing import Iterable

from reward_hack_detector.analysis.scoring import SuspicionScore


def sort_by_suspicion(scores: Iterable[SuspicionScore]) -> list[SuspicionScore]:
    return sorted(scores, key=lambda s: -s.suspicion)


def top_k(scores: Iterable[SuspicionScore], k: int) -> list[SuspicionScore]:
    if k <= 0:
        return []
    return sort_by_suspicion(scores)[:k]
