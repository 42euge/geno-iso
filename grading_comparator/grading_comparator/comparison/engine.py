"""Comparison engine.

Takes a set of graders that have all evaluated the same dataset and
produces:

* per-grader score distribution summaries
* pairwise statistics (Spearman, Kendall, agreement rate, mean diff,
  top-k overlap)
* a ranked list of the most divergent samples
* a selection-sensitivity report
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Mapping, Sequence

from ..graders.base import Grader
from ..metrics.agreement import agreement_rate, cohen_kappa, top_k_overlap
from ..metrics.bias import BiasSlice, bias_report
from ..metrics.correlation import kendall_tau, pearson, spearman
from ..metrics.distribution import ScoreSummary, describe
from .disagreement import DisagreementSample, top_disagreements
from .sensitivity import SelectionShift, selection_sensitivity


@dataclass(frozen=True)
class PairwiseStats:
    grader_a: str
    grader_b: str
    n: int
    pearson: float
    spearman: float
    kendall_tau: float
    agreement_rate: float
    mean_diff: float
    cohen_kappa: float | None
    top_k_overlap: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class ComparisonResult:
    sample_ids: list[str]
    grader_names: list[str]
    scores: dict[str, dict[str, float]]
    distributions: dict[str, ScoreSummary]
    pairwise: list[PairwiseStats]
    bias: dict[str, dict[str, object]]
    disagreements: list[DisagreementSample]
    selection_shifts: list[SelectionShift] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_ids": self.sample_ids,
            "grader_names": self.grader_names,
            "scores": self.scores,
            "distributions": {
                k: v.to_dict() for k, v in self.distributions.items()
            },
            "pairwise": [p.to_dict() for p in self.pairwise],
            "bias": {
                pair: {
                    "overall": asdict(report["overall"]),
                    "by_group": [
                        asdict(s) for s in report.get("by_group", [])
                    ],
                }
                for pair, report in self.bias.items()
            },
            "disagreements": [d.to_dict() for d in self.disagreements],
            "selection_shifts": [s.to_dict() for s in self.selection_shifts],
        }


class ComparisonEngine:
    """Compare multiple graders over a shared sample id set."""

    def __init__(
        self,
        graders: Sequence[Grader],
        scores: Mapping[str, Mapping[str, float]],
        sample_ids: Sequence[str],
        groups: Mapping[str, str] | None = None,
    ) -> None:
        self.graders = list(graders)
        self.grader_names = [g.name for g in self.graders]
        self.scores = {g: dict(s) for g, s in scores.items()}
        self.sample_ids = list(sample_ids)
        self.groups = dict(groups) if groups else None

    @classmethod
    def from_graders(
        cls,
        graders: Sequence[Grader],
        sample_ids: Sequence[str] | None = None,
        groups: Mapping[str, str] | None = None,
    ) -> "ComparisonEngine":
        """Build directly from precomputed graders, intersecting their samples."""
        per_grader: dict[str, dict[str, float]] = {}
        common: set[str] | None = None
        for g in graders:
            if not hasattr(g, "scores"):
                raise TypeError(
                    f"grader {g.name!r} has no precomputed .scores; pass scores explicitly"
                )
            per_grader[g.name] = dict(g.scores)
            keys = set(per_grader[g.name].keys())
            common = keys if common is None else common & keys
        if common is None:
            common = set()
        if sample_ids is None:
            sample_ids = sorted(common)
        else:
            missing = [s for s in sample_ids if s not in common]
            if missing:
                raise KeyError(
                    f"samples missing from one or more graders: {missing[:5]}"
                    + ("..." if len(missing) > 5 else "")
                )
        return cls(graders, per_grader, sample_ids, groups=groups)

    def _vector(self, grader_name: str) -> list[float]:
        s = self.scores[grader_name]
        return [s[i] for i in self.sample_ids]

    def run(
        self,
        binarise_threshold: float | None = None,
        top_k: int | float | None = None,
        max_disagreements: int = 20,
    ) -> ComparisonResult:
        """Compute all comparison artefacts.

        Parameters
        ----------
        binarise_threshold
            If given, compute Cohen's kappa using this threshold for both
            graders in each pair. Otherwise kappa is omitted.
        top_k
            Either an integer k or a float in (0, 1] interpreted as a
            fraction of the dataset. Used for top-k overlap and selection
            sensitivity.
        max_disagreements
            Number of most-divergent samples to include in the report.
        """
        n = len(self.sample_ids)
        vectors = {name: self._vector(name) for name in self.grader_names}
        distributions = {name: describe(vec) for name, vec in vectors.items()}

        if isinstance(top_k, float):
            if not 0 < top_k <= 1:
                raise ValueError("top_k as float must be in (0, 1]")
            k = max(1, int(round(top_k * n)))
        elif isinstance(top_k, int):
            k = max(1, min(top_k, n)) if top_k else None  # type: ignore[assignment]
        else:
            k = None

        pairwise: list[PairwiseStats] = []
        bias: dict[str, dict[str, object]] = {}
        groups_seq = (
            [self.groups[s] for s in self.sample_ids] if self.groups else None
        )

        for i, a in enumerate(self.grader_names):
            for b in self.grader_names[i + 1 :]:
                xa = vectors[a]
                xb = vectors[b]
                kappa: float | None = None
                if binarise_threshold is not None:
                    kappa = cohen_kappa(xa, xb, binarise_threshold)
                tk: float | None = None
                if k is not None:
                    tk = top_k_overlap(xa, xb, k)
                pairwise.append(
                    PairwiseStats(
                        grader_a=a,
                        grader_b=b,
                        n=n,
                        pearson=pearson(xa, xb),
                        spearman=spearman(xa, xb),
                        kendall_tau=kendall_tau(xa, xb),
                        agreement_rate=agreement_rate(
                            xa, xb, tolerance=_default_tolerance(xa, xb)
                        ),
                        mean_diff=sum(p - q for p, q in zip(xa, xb)) / n,
                        cohen_kappa=kappa,
                        top_k_overlap=tk,
                    )
                )
                bias[f"{a}__vs__{b}"] = bias_report(xa, xb, groups=groups_seq)

        disagreements = top_disagreements(
            sample_ids=self.sample_ids,
            scores=vectors,
            limit=max_disagreements,
        )

        shifts: list[SelectionShift] = []
        if k is not None:
            shifts = selection_sensitivity(self.sample_ids, vectors, k=k)

        return ComparisonResult(
            sample_ids=list(self.sample_ids),
            grader_names=list(self.grader_names),
            scores={name: dict(zip(self.sample_ids, vec)) for name, vec in vectors.items()},
            distributions=distributions,
            pairwise=pairwise,
            bias=bias,
            disagreements=disagreements,
            selection_shifts=shifts,
        )


def _default_tolerance(a: Sequence[float], b: Sequence[float]) -> float:
    """Tolerance for ``agreement_rate`` based on the joint score range.

    With heterogeneous score scales (e.g. rubric on [0,1] vs reward
    model logits) an exact-equality definition of "agreement" is rarely
    meaningful. We use 5% of the joint range as a default.
    """
    combined = list(a) + list(b)
    if not combined:
        return 0.0
    span = max(combined) - min(combined)
    return 0.05 * span if span > 0 else 0.0
