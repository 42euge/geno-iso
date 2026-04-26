"""Lexical signals: tokenization, similarity, repetition, overlap."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

_WORD = re.compile(r"\w+", re.UNICODE)

# Common English stop words; small list intentional (avoid heavy deps).
STOP_WORDS = frozenset(
    """
a about above after again against all am an and any are as at be because been before
being below between both but by can did do does doing don down during each few for
from further had has have having he her here hers herself him himself his how i if in
into is it its itself just me more most my myself no nor not now of off on once only
or other our ours ourselves out over own same she should so some such than that the
their theirs them themselves then there these they this those through to too under
until up very was we were what when where which while who whom why will with you your
yours yourself yourselves
""".split()
)


def tokenize(text: str, *, lower: bool = True, drop_stop: bool = False) -> list[str]:
    if not text:
        return []
    toks = _WORD.findall(text.lower() if lower else text)
    if drop_stop:
        toks = [t for t in toks if t not in STOP_WORDS]
    return toks


def _vec(text: str) -> Counter:
    return Counter(tokenize(text))


def bow_cosine(a: str, b: str) -> float:
    """Cosine similarity of bag-of-words count vectors. Range [0, 1]."""

    va, vb = _vec(a), _vec(b)
    if not va or not vb:
        return 0.0
    common = set(va) & set(vb)
    if not common:
        return 0.0
    num = sum(va[w] * vb[w] for w in common)
    da = math.sqrt(sum(v * v for v in va.values()))
    db = math.sqrt(sum(v * v for v in vb.values()))
    if da == 0.0 or db == 0.0:
        return 0.0
    return num / (da * db)


def jaccard(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def ngram_repetition(text: str, n: int = 3) -> float:
    """Fraction of n-grams that are duplicates of an earlier n-gram. [0, 1]."""

    toks = tokenize(text)
    if len(toks) < n:
        return 0.0
    grams = [tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)]
    counts = Counter(grams)
    repeated = sum(c - 1 for c in counts.values() if c > 1)
    return repeated / len(grams)


def keyword_overlap(output: str, prompt: str) -> float:
    """Fraction of output content tokens that simply echo prompt tokens.

    Stop words are dropped to avoid trivially-high overlap from function words.
    """

    out_toks = [t for t in tokenize(output) if t not in STOP_WORDS]
    prompt_toks = {t for t in tokenize(prompt) if t not in STOP_WORDS}
    if not out_toks:
        return 0.0
    return sum(1 for t in out_toks if t in prompt_toks) / len(out_toks)


def type_token_ratio(text: str) -> float:
    """Lexical diversity: unique tokens / total tokens. Lower = more repetitive."""

    toks = tokenize(text)
    if not toks:
        return 0.0
    return len(set(toks)) / len(toks)


def density_of(words: Iterable[str], text: str) -> float:
    toks = tokenize(text)
    if not toks:
        return 0.0
    target = set(words)
    return sum(1 for t in toks if t in target) / len(toks)
