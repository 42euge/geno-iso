"""Factory: build graders from config dictionaries."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .base import Grader
from .heuristic import HeuristicFileGrader
from .preference import PreferenceModelGrader
from .precomputed import PrecomputedGrader
from .rubric import RubricFileGrader

_TYPE_MAP: dict[str, type[PrecomputedGrader]] = {
    "rubric": RubricFileGrader,
    "preference_model": PreferenceModelGrader,
    "preference": PreferenceModelGrader,
    "heuristic": HeuristicFileGrader,
    "precomputed": PrecomputedGrader,
}


def load_grader(config: Mapping[str, Any], base_dir: Path | None = None) -> Grader:
    """Build a grader from a config entry.

    Expected keys:
        name: human-readable identifier (required)
        type: one of rubric|preference_model|heuristic|precomputed (required)
        path: path to the precomputed scores file (required)
        sample_col: column / key holding the sample id (default "sample_id")
        score_col:  column / key holding the score      (default "score")
    """
    try:
        name = config["name"]
        kind = config["type"]
        raw_path = config["path"]
    except KeyError as exc:
        raise ValueError(f"grader config missing required key: {exc.args[0]}") from exc

    cls = _TYPE_MAP.get(kind)
    if cls is None:
        raise ValueError(
            f"unknown grader type {kind!r}; expected one of {sorted(_TYPE_MAP)}"
        )

    path = Path(raw_path)
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path

    return cls(
        name=name,
        path=path,
        sample_col=config.get("sample_col", "sample_id"),
        score_col=config.get("score_col", "score"),
    )


def load_all_graders(
    configs: Sequence[Mapping[str, Any]], base_dir: Path | None = None
) -> list[Grader]:
    graders = [load_grader(c, base_dir=base_dir) for c in configs]
    names = [g.name for g in graders]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate grader names in config: {names}")
    return graders
