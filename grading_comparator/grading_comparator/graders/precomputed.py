"""Graders backed by precomputed score files (CSV / JSONL)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Mapping

from .base import Grader, GraderResult, Sample


def _read_scores(path: Path, sample_col: str, score_col: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        delim = "," if suffix == ".csv" else "\t"
        with path.open(newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)
            for row in reader:
                if sample_col not in row or score_col not in row:
                    raise KeyError(
                        f"{path}: row missing required columns "
                        f"{sample_col!r}/{score_col!r}: {row}"
                    )
                scores[row[sample_col]] = float(row[score_col])
    elif suffix in {".jsonl", ".ndjson"}:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                scores[str(row[sample_col])] = float(row[score_col])
    elif suffix == ".json":
        with path.open() as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k, v in data.items():
                scores[str(k)] = float(v)
        else:
            for row in data:
                scores[str(row[sample_col])] = float(row[score_col])
    else:
        raise ValueError(f"Unsupported scores file format: {path}")
    return scores


class PrecomputedGrader(Grader):
    """A grader whose scores have already been computed and stored on disk.

    This is the workhorse for offline comparison: each grading method
    (rubric A, rubric B, a preference model, a heuristic) writes its
    scores to a file, and we load them through this adapter.
    """

    def __init__(
        self,
        name: str,
        path: str | Path,
        sample_col: str = "sample_id",
        score_col: str = "score",
    ) -> None:
        super().__init__(name)
        self.path = Path(path)
        self.sample_col = sample_col
        self.score_col = score_col
        self._scores: Mapping[str, float] = _read_scores(
            self.path, sample_col, score_col
        )

    @property
    def scores(self) -> Mapping[str, float]:
        return self._scores

    def score(self, sample: Sample) -> GraderResult:
        if sample.sample_id not in self._scores:
            raise KeyError(
                f"grader {self.name!r}: no precomputed score for sample "
                f"{sample.sample_id!r}"
            )
        return GraderResult(
            grader=self.name,
            sample_id=sample.sample_id,
            score=self._scores[sample.sample_id],
        )
