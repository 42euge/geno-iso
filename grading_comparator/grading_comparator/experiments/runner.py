"""End-to-end experiment runner: config -> graders -> comparison -> reports."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from ..comparison.engine import ComparisonEngine, ComparisonResult
from ..graders import load_all_graders
from .config import ExperimentConfig, load_dataset_metadata


def run_experiment(config: ExperimentConfig) -> ComparisonResult:
    graders = load_all_graders(config.graders, base_dir=config.base_dir)

    sample_ids: Sequence[str] | None = None
    groups: dict[str, str] | None = None
    if config.dataset_path is not None:
        sample_ids, groups = load_dataset_metadata(
            config.dataset_path,
            config.sample_id_col,
            config.group_col,
        )

    engine = ComparisonEngine.from_graders(
        graders, sample_ids=sample_ids, groups=groups
    )
    return engine.run(
        binarise_threshold=config.binarise_threshold,
        top_k=config.top_k,
        max_disagreements=config.max_disagreements,
    )


def write_reports(
    result: ComparisonResult,
    output_dir: Path,
    plots: bool = False,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    summary_path = output_dir / "summary.json"
    with summary_path.open("w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)
    paths["summary"] = summary_path

    pairwise_path = output_dir / "pairwise_metrics.csv"
    with pairwise_path.open("w", newline="") as f:
        if result.pairwise:
            writer = csv.DictWriter(f, fieldnames=list(asdict(result.pairwise[0])))
            writer.writeheader()
            for p in result.pairwise:
                writer.writerow(asdict(p))
    paths["pairwise"] = pairwise_path

    disagreement_path = output_dir / "top_disagreements.csv"
    with disagreement_path.open("w", newline="") as f:
        writer = csv.writer(f)
        header = ["sample_id", "disagreement"]
        for g in result.grader_names:
            header.append(f"score:{g}")
        for g in result.grader_names:
            header.append(f"z:{g}")
        writer.writerow(header)
        for d in result.disagreements:
            row = [d.sample_id, f"{d.disagreement:.6f}"]
            for g in result.grader_names:
                row.append(f"{d.scores.get(g, float('nan')):.6f}")
            for g in result.grader_names:
                row.append(f"{d.standardised.get(g, float('nan')):.6f}")
            writer.writerow(row)
    paths["disagreements"] = disagreement_path

    distributions_path = output_dir / "distributions.csv"
    with distributions_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["grader", "n", "mean", "std", "min", "q25", "median", "q75", "max"])
        for name, summ in result.distributions.items():
            writer.writerow([
                name, summ.n,
                f"{summ.mean:.6f}", f"{summ.std:.6f}",
                f"{summ.minimum:.6f}", f"{summ.q25:.6f}",
                f"{summ.median:.6f}", f"{summ.q75:.6f}",
                f"{summ.maximum:.6f}",
            ])
    paths["distributions"] = distributions_path

    if result.selection_shifts:
        shifts_path = output_dir / "selection_shifts.csv"
        with shifts_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "grader_a", "grader_b", "k", "overlap", "jaccard",
                "only_a", "only_b",
            ])
            for s in result.selection_shifts:
                writer.writerow([
                    s.grader_a, s.grader_b, s.k, s.overlap,
                    f"{s.jaccard:.6f}",
                    "|".join(s.only_a), "|".join(s.only_b),
                ])
        paths["selection_shifts"] = shifts_path

    if plots:
        try:
            from ..plotting.plots import write_plots

            plot_paths = write_plots(result, output_dir / "plots")
            paths.update(plot_paths)
        except ImportError as exc:
            paths["plots_error"] = Path(f"matplotlib not available: {exc}")

    return paths
