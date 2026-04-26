"""Tests for the metrics module — verified against scipy reference values."""
import math

import pytest

from grading_comparator.metrics import (
    agreement_rate,
    binarised_agreement,
    cohen_kappa,
    describe,
    kendall_tau,
    pearson,
    rankdata,
    spearman,
    top_k_overlap,
)
from grading_comparator.metrics.bias import bias_report, mean_difference


def test_rankdata_handles_ties():
    assert rankdata([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_pearson_perfect_positive():
    assert pearson([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)


def test_pearson_perfect_negative():
    assert pearson([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_spearman_monotonic_nonlinear():
    # Monotonic non-linear => spearman = 1, pearson < 1
    x = [1, 2, 3, 4, 5]
    y = [1, 4, 9, 16, 25]
    assert spearman(x, y) == pytest.approx(1.0)
    assert pearson(x, y) < 1.0


def test_kendall_tau_perfect():
    x = [1, 2, 3, 4]
    y = [10, 20, 30, 40]
    assert kendall_tau(x, y) == pytest.approx(1.0)


def test_kendall_tau_known_value():
    # 4 pairs: (1,2,3,4) vs (1,3,2,4) — one discordant pair (2 vs 3),
    # so tau = (5 - 1) / 6 = 4/6 ≈ 0.6667
    x = [1, 2, 3, 4]
    y = [1, 3, 2, 4]
    assert kendall_tau(x, y) == pytest.approx(2 / 3, rel=1e-6)


def test_kendall_tau_b_with_ties():
    # All ties in y -> denominator is 0 -> NaN
    assert math.isnan(kendall_tau([1, 2, 3], [5, 5, 5]))


def test_agreement_rate_with_tolerance():
    a = [1.0, 2.0, 3.0]
    b = [1.05, 2.0, 3.5]
    assert agreement_rate(a, b, tolerance=0.1) == pytest.approx(2 / 3)
    assert agreement_rate(a, b, tolerance=1.0) == 1.0


def test_binarised_agreement():
    a = [0.9, 0.6, 0.4, 0.8]
    b = [0.7, 0.3, 0.5, 0.9]
    # threshold 0.5: a -> [T,T,F,T], b -> [T,F,T,T]; matches = 2/4
    assert binarised_agreement(a, b, 0.5) == pytest.approx(0.5)


def test_cohen_kappa_perfect():
    a = [0.9, 0.8, 0.1, 0.2]
    b = [0.95, 0.75, 0.0, 0.3]
    assert cohen_kappa(a, b, 0.5) == pytest.approx(1.0)


def test_top_k_overlap():
    a = [1, 2, 3, 4, 5]
    b = [5, 4, 3, 2, 1]  # reversed
    # top 2 of a = {3, 4}, top 2 of b = {0, 1} (indices) => no overlap
    assert top_k_overlap(a, b, 2) == 0.0
    # top 5 = full set => overlap 1.0
    assert top_k_overlap(a, b, 5) == 1.0


def test_describe_basic():
    summ = describe([1.0, 2.0, 3.0, 4.0, 5.0])
    assert summ.n == 5
    assert summ.mean == pytest.approx(3.0)
    assert summ.median == pytest.approx(3.0)
    assert summ.minimum == 1.0
    assert summ.maximum == 5.0


def test_mean_difference_and_bias_report():
    x = [1.0, 2.0, 3.0, 4.0]
    y = [0.0, 1.0, 2.0, 3.0]
    assert mean_difference(x, y) == pytest.approx(1.0)
    rep = bias_report(x, y, groups=["a", "a", "b", "b"])
    assert rep["overall"].mean_diff == pytest.approx(1.0)
    by_group = {s.group: s for s in rep["by_group"]}
    assert by_group["a"].mean_diff == pytest.approx(1.0)
    assert by_group["b"].mean_diff == pytest.approx(1.0)
