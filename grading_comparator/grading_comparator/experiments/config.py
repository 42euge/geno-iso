"""Experiment config loader."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


@dataclass
class ExperimentConfig:
    name: str
    graders: list[dict[str, Any]]
    output_dir: Path
    dataset_path: Path | None = None
    sample_id_col: str = "sample_id"
    group_col: str | None = None
    binarise_threshold: float | None = None
    top_k: int | float | None = None
    max_disagreements: int = 20
    plots: bool = False
    base_dir: Path = field(default_factory=lambda: Path.cwd())

    @property
    def resolved_output_dir(self) -> Path:
        return self.output_dir if self.output_dir.is_absolute() else self.base_dir / self.output_dir


def _resolve(p: str | Path | None, base: Path) -> Path | None:
    if p is None:
        return None
    path = Path(p)
    return path if path.is_absolute() else base / path


def load_config(path: str | Path) -> ExperimentConfig:
    cfg_path = Path(path).resolve()
    with cfg_path.open() as f:
        data: Mapping[str, Any] = yaml.safe_load(f) or {}

    base_dir = cfg_path.parent

    try:
        name = data["name"]
        graders = list(data["graders"])
        output_dir = _resolve(data["output_dir"], base_dir)
    except KeyError as exc:
        raise ValueError(f"config missing required key: {exc.args[0]}") from exc

    if not graders:
        raise ValueError("config must list at least one grader")
    if output_dir is None:
        raise ValueError("config.output_dir is required")

    dataset = data.get("dataset", {})
    return ExperimentConfig(
        name=name,
        graders=graders,
        output_dir=output_dir,
        dataset_path=_resolve(dataset.get("path"), base_dir),
        sample_id_col=dataset.get("sample_id_col", "sample_id"),
        group_col=dataset.get("group_col"),
        binarise_threshold=data.get("binarise_threshold"),
        top_k=data.get("top_k"),
        max_disagreements=int(data.get("max_disagreements", 20)),
        plots=bool(data.get("plots", False)),
        base_dir=base_dir,
    )


def load_dataset_metadata(
    path: Path,
    sample_id_col: str,
    group_col: str | None,
) -> tuple[list[str], dict[str, str] | None]:
    """Load sample ordering (and optional group labels) from a CSV/JSONL/JSON."""
    import csv
    import json

    suffix = path.suffix.lower()
    sample_ids: list[str] = []
    groups: dict[str, str] | None = {} if group_col else None
    if suffix in {".csv", ".tsv"}:
        delim = "," if suffix == ".csv" else "\t"
        with path.open(newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)
            for row in reader:
                sid = row[sample_id_col]
                sample_ids.append(sid)
                if groups is not None and group_col in row:
                    groups[sid] = row[group_col]
    elif suffix in {".jsonl", ".ndjson"}:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                sid = str(row[sample_id_col])
                sample_ids.append(sid)
                if groups is not None and group_col in row:
                    groups[sid] = str(row[group_col])
    elif suffix == ".json":
        with path.open() as f:
            rows = json.load(f)
        for row in rows:
            sid = str(row[sample_id_col])
            sample_ids.append(sid)
            if groups is not None and group_col in row:
                groups[sid] = str(row[group_col])
    else:
        raise ValueError(f"unsupported dataset format: {path}")
    return sample_ids, groups
