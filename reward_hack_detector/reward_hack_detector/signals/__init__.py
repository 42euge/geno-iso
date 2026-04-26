"""Heuristic and learned signals used by detectors."""

from reward_hack_detector.signals.length import (
    char_length,
    token_length,
    length_zscore,
)
from reward_hack_detector.signals.lexical import (
    tokenize,
    bow_cosine,
    jaccard,
    ngram_repetition,
    keyword_overlap,
    type_token_ratio,
)
from reward_hack_detector.signals.format import format_density, code_fence_count
from reward_hack_detector.signals.confidence import (
    confidence_ratios,
    HEDGE_WORDS,
    STRONG_WORDS,
)
from reward_hack_detector.signals.embedding import EmbeddingSignal

__all__ = [
    "char_length",
    "token_length",
    "length_zscore",
    "tokenize",
    "bow_cosine",
    "jaccard",
    "ngram_repetition",
    "keyword_overlap",
    "type_token_ratio",
    "format_density",
    "code_fence_count",
    "confidence_ratios",
    "HEDGE_WORDS",
    "STRONG_WORDS",
    "EmbeddingSignal",
]
