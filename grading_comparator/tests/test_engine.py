"""End-to-end tests for the comparison engine and disagreement utilities."""
import math
from pathlib import Path

import pytest

from grading_comparator.comparison.disagreement import top_disagreements
from grading_comparator.comparison.engine import ComparisonEngine
from grading_comparator.comparison.sensitivity import selection_sensitivity
from grading_comparator.graders.precomputed import PrecomputedGrader


def test_engine_with_two_graders():
    sample_ids = [f"s{i}" for i in range(10)]
    a = {s: i for i, s in enumerate(sample_ids)}
    b = {s: i * 2 for i, s in enumerate(sample_ids)}  # monotonic in a

    class _Stub:
        def __init__(self, name, scores):
            self.name = name
            self.scores = scores

    engine = ComparisonEngine.from_graders(
        [_Stub("a", a), _Stub("b", b)], sample_ids=sample_ids,
    )
    res = engine.run(top_k=0.3, max_disagreements=3)

    assert res.grader_names == ["a", "b"]
    assert len(res.pairwise) == 1
    p = res.pairwise[0]
    assert p.spearman == pytest.approx(1.0)
    assert p.kendall_tau == pytest.approx(1.0)
    assert p.top_k_overlap == pytest.approx(1.0)
    assert p.mean_diff < 0  # b is larger than a


def test_disagreement_ordering():
    sample_ids = ["x", "y", "z"]
    scores = {
        "g1": [0.1, 0.5, 0.9],
        "g2": [0.9, 0.5, 0.1],   # full reversal -> x and z disagree
    }
    out = top_disagreements(sample_ids, scores, limit=3)
    assert out[0].sample_id in {"x", "z"}
    assert out[-1].sample_id == "y"
    assert out[0].disagreement >= out[-1].disagreement


def test_selection_sensitivity_disjoint_top_k():
    sample_ids = ["a", "b", "c", "d"]
    scores = {
        "g1": [10, 9, 1, 2],   # top 2 = a, b
        "g2": [1, 2, 10, 9],   # top 2 = c, d
    }
    shifts = selection_sensitivity(sample_ids, scores, k=2)
    assert len(shifts) == 1
    s = shifts[0]
    assert s.k == 2
    assert s.overlap == 0
    assert s.jaccard == 0.0
    assert sorted(s.only_a) == ["a", "b"]
    assert sorted(s.only_b) == ["c", "d"]


def test_precomputed_grader_loads_csv(tmp_path: Path):
    p = tmp_path / "scores.csv"
    p.write_text("sample_id,score\nx,1.0\ny,2.0\n")
    g = PrecomputedGrader("test", p)
    assert g.scores == {"x": 1.0, "y": 2.0}


def test_full_example_config_runs(tmp_path: Path):
    """Smoke test against the shipped example config."""
    from grading_comparator.experiments.config import load_config
    from grading_comparator.experiments.runner import run_experiment, write_reports

    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_config(repo_root / "configs" / "example.yaml")
    cfg.output_dir = tmp_path / "out"
    result = run_experiment(cfg)

    assert len(result.sample_ids) == 30
    assert set(result.grader_names) == {
        "rubric_a", "rubric_b", "preference_model", "heuristic_length",
    }
    # 4 graders => 6 unordered pairs
    assert len(result.pairwise) == 6

    # Rubric A vs Rubric B should agree more (higher spearman) than
    # rubric A vs the length heuristic — that's the whole point of the demo.
    by_pair = {(p.grader_a, p.grader_b): p for p in result.pairwise}
    rubric_pair = by_pair[("rubric_a", "rubric_b")]
    heuristic_pair = by_pair[("rubric_a", "heuristic_length")]
    assert rubric_pair.spearman > heuristic_pair.spearman
    assert not math.isnan(rubric_pair.kendall_tau)

    paths = write_reports(result, cfg.resolved_output_dir, plots=False)
    for label in ("summary", "pairwise", "disagreements", "distributions"):
        assert paths[label].exists()
