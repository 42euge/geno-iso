"""Load rubric definitions from YAML or JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from rubric_harness.rubrics.schema import (
    Criterion,
    MultiCriteriaRubric,
    PairwiseRubric,
    Rubric,
    RubricKind,
    ScalarRubric,
)


def load_rubric(path: str | Path) -> Rubric:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"rubric file not found: {p}")
    text = p.read_text()
    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    elif p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        raise ValueError(f"unsupported rubric extension: {p.suffix} (use .yaml/.yml/.json)")
    return load_rubric_dict(data)


def load_rubric_dict(data: dict[str, Any]) -> Rubric:
    if not isinstance(data, dict):
        raise ValueError(f"rubric definition must be a mapping, got {type(data).__name__}")

    kind_str = data.get("kind")
    if kind_str is None:
        raise ValueError("rubric definition missing required field 'kind'")
    try:
        kind = RubricKind(kind_str)
    except ValueError as e:
        raise ValueError(
            f"invalid rubric kind '{kind_str}'; expected one of "
            f"{[k.value for k in RubricKind]}"
        ) from e

    common = {
        "name": _required(data, "name"),
        "description": data.get("description", ""),
        "judge_prompt_template": _required(data, "judge_prompt_template"),
        "version": data.get("version", "0.1.0"),
        "metadata": data.get("metadata", {}) or {},
    }

    if kind is RubricKind.SCALAR:
        return ScalarRubric(
            **common,
            scale_min=int(data.get("scale_min", 1)),
            scale_max=int(data.get("scale_max", 5)),
        )

    if kind is RubricKind.PAIRWISE:
        labels = data.get("labels", ["A", "B"])
        return PairwiseRubric(
            **common,
            allow_tie=bool(data.get("allow_tie", True)),
            labels=tuple(labels),
        )

    if kind is RubricKind.MULTI_CRITERIA:
        raw_criteria = data.get("criteria") or []
        criteria = [
            Criterion(
                name=_required(c, "name"),
                description=c.get("description", ""),
                scale_min=int(c.get("scale_min", 1)),
                scale_max=int(c.get("scale_max", 5)),
                weight=float(c.get("weight", 1.0)),
            )
            for c in raw_criteria
        ]
        return MultiCriteriaRubric(**common, criteria=criteria)

    raise AssertionError(f"unhandled rubric kind: {kind}")  # pragma: no cover


def _required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"rubric definition missing required field '{key}'")
    return data[key]
