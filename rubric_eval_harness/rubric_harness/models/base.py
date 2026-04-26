"""Abstract model client interface.

A `ModelClient` produces a text completion for a single prompt. Implementations
are expected to be cheap to construct in deterministic mode and may lazily load
heavy dependencies (HF transformers, llama.cpp, network clients).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationRequest:
    prompt: str
    max_new_tokens: int = 256
    temperature: float = 0.0
    seed: int | None = None
    stop: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)


class ModelClient(ABC):
    """Base class for all model backends."""

    name: str = "model"

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        ...

    def generate_batch(self, requests: list[GenerationRequest]) -> list[GenerationResult]:
        return [self.generate(r) for r in requests]

    def close(self) -> None:
        """Release any held resources. Default is a no-op."""
        return None
