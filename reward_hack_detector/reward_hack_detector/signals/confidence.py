"""Confidence / hedging language signals."""

from __future__ import annotations

import re

from reward_hack_detector.signals.lexical import tokenize

STRONG_WORDS = frozenset(
    {
        "definitely",
        "certainly",
        "absolutely",
        "undoubtedly",
        "guaranteed",
        "always",
        "never",
        "must",
        "cannot",
        "impossible",
        "obvious",
        "obviously",
        "clearly",
        "indisputable",
        "undeniable",
        "everyone",
        "nobody",
        "all",
        "none",
    }
)

HEDGE_WORDS = frozenset(
    {
        "may",
        "might",
        "could",
        "perhaps",
        "possibly",
        "likely",
        "seems",
        "appears",
        "suggests",
        "approximately",
        "roughly",
        "tends",
        "often",
        "sometimes",
        "usually",
        "uncertain",
    }
)

_PERCENT_100 = re.compile(r"\b100\s?%")
_HARD_NUMBERS = re.compile(r"\b\d{2,}(\.\d+)?\b")


def confidence_ratios(text: str) -> dict[str, float]:
    """Return strong/hedge token ratios plus a 100%-claim flag."""

    toks = tokenize(text)
    n = len(toks) or 1
    strong = sum(1 for t in toks if t in STRONG_WORDS) / n
    hedge = sum(1 for t in toks if t in HEDGE_WORDS) / n
    pct_100 = 1.0 if _PERCENT_100.search(text or "") else 0.0
    hard_numbers = len(_HARD_NUMBERS.findall(text or "")) / n
    return {
        "strong_ratio": strong,
        "hedge_ratio": hedge,
        "pct_100_claim": pct_100,
        "hard_number_density": hard_numbers,
    }
