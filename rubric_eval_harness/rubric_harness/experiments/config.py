"""Experiment configuration model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ExperimentConfig:
    name: str
    rubric: str  # path to rubric file
    dataset: str  # path to JSONL dataset
    output_dir: str = "outputs"

    judge: dict[str, Any] = field(default_factory=lambda: {"backend": "mock"})
    candidate: dict[str, Any] | None = None  # if set, generate responses

    mode: str = "batch"  # "batch" | "stream"
    deterministic: bool = True
    seed: int = 0
    temperature: float = 0.0
    max_new_tokens: int = 256
    limit: int | None = None  # cap dataset size for fast iteration
    visualize: bool = False

    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_temperature(self) -> float:
        return 0.0 if self.deterministic else self.temperature

    @property
    def effective_seed(self) -> int | None:
        return self.seed if self.deterministic else None


def load_config(path: str | Path) -> ExperimentConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config file not found: {p}")
    text = p.read_text()
    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    elif p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        raise ValueError(f"unsupported config extension: {p.suffix}")

    if not isinstance(data, dict):
        raise ValueError("config must be a mapping")

    base_dir = p.parent

    def _resolve(field_value: str) -> str:
        candidate_path = Path(field_value)
        if candidate_path.is_absolute() or candidate_path.exists():
            return str(candidate_path)
        return str((base_dir / candidate_path).resolve())

    return ExperimentConfig(
        name=data.get("name", p.stem),
        rubric=_resolve(_required(data, "rubric")),
        dataset=_resolve(_required(data, "dataset")),
        output_dir=data.get("output_dir", "outputs"),
        judge=data.get("judge") or {"backend": "mock"},
        candidate=data.get("candidate"),
        mode=data.get("mode", "batch"),
        deterministic=bool(data.get("deterministic", True)),
        seed=int(data.get("seed", 0)),
        temperature=float(data.get("temperature", 0.0)),
        max_new_tokens=int(data.get("max_new_tokens", 256)),
        limit=data.get("limit"),
        visualize=bool(data.get("visualize", False)),
        raw=data,
    )


def _required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"config missing required field '{key}'")
    return data[key]
