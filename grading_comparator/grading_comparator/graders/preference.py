"""Preference model grader.

A preference model produces a scalar reward / preference score per sample.
Here we simply load those scores from disk via :class:`PrecomputedGrader`.
"""
from __future__ import annotations

from .precomputed import PrecomputedGrader


class PreferenceModelGrader(PrecomputedGrader):
    kind = "preference_model"
