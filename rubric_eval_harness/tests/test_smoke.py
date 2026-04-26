"""End-to-end smoke tests using the mock model (no external deps)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rubric_harness.evaluation import EvaluationItem, evaluate
from rubric_harness.experiments import load_config
from rubric_harness.experiments.runner import ExperimentRunner
from rubric_harness.models import MockModel
from rubric_harness.rubrics import load_rubric


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize(
    "rubric_file,needs_b",
    [
        ("rubrics/scalar_helpfulness.yaml", False),
        ("rubrics/pairwise_quality.yaml", True),
        ("rubrics/multi_criteria.yaml", False),
    ],
)
def test_evaluate_each_rubric_kind(rubric_file: str, needs_b: bool) -> None:
    rubric = load_rubric(EXAMPLES / rubric_file)
    judge = MockModel(default_seed=0)
    item = EvaluationItem(
        item_id="t1",
        prompt="What is 2+2?",
        response="4",
        response_b="22" if needs_b else None,
    )
    out = evaluate([item], rubric, judge)
    assert len(out) == 1
    assert out[0].parse_ok, out[0].parse_error


@pytest.mark.parametrize(
    "config_file",
    [
        "configs/scalar_helpfulness.yaml",
        "configs/pairwise_quality.yaml",
        "configs/multi_criteria.yaml",
    ],
)
def test_runner_end_to_end(tmp_path: Path, config_file: str) -> None:
    cfg = load_config(EXAMPLES / config_file)
    cfg.output_dir = str(tmp_path)
    cfg.limit = 4
    summary = ExperimentRunner(cfg).run()
    assert summary.n_items == 4

    out_dir = Path(summary.output_dir)
    assert (out_dir / "results.jsonl").exists()
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "summary.txt").exists()

    rows = [json.loads(l) for l in (out_dir / "results.jsonl").read_text().splitlines()]
    assert len(rows) == 4


def test_deterministic_mode_is_reproducible(tmp_path: Path) -> None:
    cfg = load_config(EXAMPLES / "configs/scalar_helpfulness.yaml")
    cfg.output_dir = str(tmp_path / "a")
    s1 = ExperimentRunner(cfg).run()

    cfg2 = load_config(EXAMPLES / "configs/scalar_helpfulness.yaml")
    cfg2.output_dir = str(tmp_path / "b")
    s2 = ExperimentRunner(cfg2).run()

    a = (Path(s1.output_dir) / "results.jsonl").read_text()
    b = (Path(s2.output_dir) / "results.jsonl").read_text()
    assert a == b
