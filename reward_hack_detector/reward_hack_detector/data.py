"""Sample dataclass and JSONL loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator


@dataclass
class Sample:
    """One (prompt, output, reward) tuple, optionally with a reference."""

    prompt: str
    output: str
    reward: float
    reference: str | None = None
    id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], fallback_id: str | None = None) -> "Sample":
        if "output" not in raw and "response" in raw:
            output = raw["response"]
        else:
            output = raw.get("output", "")
        if "reward" not in raw and "score" in raw:
            reward = raw["score"]
        else:
            reward = raw.get("reward", 0.0)
        return cls(
            prompt=raw.get("prompt", ""),
            output=output,
            reward=float(reward),
            reference=raw.get("reference") or raw.get("ground_truth"),
            id=raw.get("id", fallback_id),
            metadata={
                k: v
                for k, v in raw.items()
                if k
                not in {
                    "prompt",
                    "output",
                    "response",
                    "reward",
                    "score",
                    "reference",
                    "ground_truth",
                    "id",
                }
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "output": self.output,
            "reward": self.reward,
            "reference": self.reference,
            "metadata": self.metadata,
        }


def load_jsonl(path: str | Path) -> list[Sample]:
    """Load a JSONL file into a list of ``Sample`` objects."""

    p = Path(path)
    samples: list[Sample] = []
    with p.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {idx + 1} of {p}: {exc}") from exc
            samples.append(Sample.from_dict(raw, fallback_id=f"sample_{idx:04d}"))
    return samples


def iter_jsonl(lines: Iterable[str]) -> Iterator[Sample]:
    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        yield Sample.from_dict(raw, fallback_id=f"sample_{idx:04d}")
