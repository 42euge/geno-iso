"""Formatting / structural signals."""

from __future__ import annotations

import re

_BULLET_LINE = re.compile(r"^\s*([-*+•]|\d+[.)])\s+")
_HEADER_LINE = re.compile(r"^\s*#{1,6}\s+\S")
_BLOCKQUOTE = re.compile(r"^\s*>\s+")
_BOLD_OR_ITALIC = re.compile(r"(\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*)")
_INLINE_CODE = re.compile(r"`[^`]+`")


def code_fence_count(text: str) -> int:
    return (text or "").count("```")


def format_density(text: str) -> dict[str, float]:
    """Per-line/structural-density features in [0, 1]."""

    if not text:
        return {
            "bullet_ratio": 0.0,
            "header_ratio": 0.0,
            "blockquote_ratio": 0.0,
            "structural_ratio": 0.0,
            "emphasis_density": 0.0,
            "inline_code_density": 0.0,
        }
    lines = text.splitlines() or [text]
    n = max(1, len(lines))
    bullets = sum(1 for ln in lines if _BULLET_LINE.match(ln))
    headers = sum(1 for ln in lines if _HEADER_LINE.match(ln))
    quotes = sum(1 for ln in lines if _BLOCKQUOTE.match(ln))
    structural = bullets + headers + quotes
    chars = max(1, len(text))
    emphasis_chars = sum(len(m.group(0)) for m in _BOLD_OR_ITALIC.finditer(text))
    inline_chars = sum(len(m.group(0)) for m in _INLINE_CODE.finditer(text))
    return {
        "bullet_ratio": bullets / n,
        "header_ratio": headers / n,
        "blockquote_ratio": quotes / n,
        "structural_ratio": min(1.0, structural / n),
        "emphasis_density": min(1.0, emphasis_chars / chars),
        "inline_code_density": min(1.0, inline_chars / chars),
    }
