"""Deterministic mock model for tests, debugging, and offline examples.

The mock model produces reproducible outputs by hashing the prompt. It also
recognises judge-style prompts that ask for a score in a known format and emits
a syntactically valid response, so the full pipeline can be exercised without
any external dependencies.
"""

from __future__ import annotations

import hashlib
import json
import random
import re

from rubric_harness.models.base import GenerationRequest, GenerationResult, ModelClient


_SCALAR_HINT = re.compile(r"score\s+between\s+(\d+)\s+and\s+(\d+)", re.IGNORECASE)
_PAIRWISE_HINT = re.compile(r"choose\s+(?:between\s+)?([A-Z])\s+(?:or|and|,)\s+([A-Z])", re.IGNORECASE)
_MULTI_HINT = re.compile(r"return\s+json", re.IGNORECASE)
_CRITERION_HINT = re.compile(r'-\s+"?([A-Za-z0-9_]+)"?:', re.MULTILINE)


def _seeded_rng(prompt: str, seed: int | None) -> random.Random:
    h = hashlib.sha256()
    h.update(prompt.encode("utf-8"))
    if seed is not None:
        h.update(str(seed).encode("utf-8"))
    return random.Random(int.from_bytes(h.digest()[:8], "big"))


class MockModel(ModelClient):
    """Generates structurally valid judge responses without external calls."""

    def __init__(self, name: str = "mock", default_seed: int | None = 0) -> None:
        self.name = name
        self.default_seed = default_seed

    def generate(self, request: GenerationRequest) -> GenerationResult:
        seed = request.seed if request.seed is not None else self.default_seed
        rng = _seeded_rng(request.prompt, seed)

        text = self._respond(request.prompt, rng)
        return GenerationResult(
            text=text,
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(text.split()),
            finish_reason="stop",
            raw={"backend": "mock", "seed": seed},
        )

    @staticmethod
    def _respond(prompt: str, rng: random.Random) -> str:
        m = _SCALAR_HINT.search(prompt)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            return f"Score: {rng.randint(lo, hi)}"

        m = _PAIRWISE_HINT.search(prompt)
        if m:
            choices = [m.group(1).upper(), m.group(2).upper()]
            if "tie" in prompt.lower():
                choices.append("TIE")
            return f"Verdict: {rng.choice(choices)}"

        if _MULTI_HINT.search(prompt):
            criteria = _CRITERION_HINT.findall(prompt)
            if criteria:
                payload = {c: rng.randint(1, 5) for c in criteria}
                return json.dumps(payload)

        words = ["lorem", "ipsum", "dolor", "sit", "amet"]
        rng.shuffle(words)
        return " ".join(words)
