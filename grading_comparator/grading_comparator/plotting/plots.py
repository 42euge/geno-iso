"""Histograms and pairwise scatter plots.

Imports matplotlib lazily so the rest of the package stays usable
without the optional dependency installed.
"""
from __future__ import annotations

from pathlib import Path

from ..comparison.engine import ComparisonResult


def write_plots(result: ComparisonResult, output_dir: Path) -> dict[str, Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    n_graders = len(result.grader_names)
    fig, axes = plt.subplots(1, n_graders, figsize=(4 * n_graders, 3.5), squeeze=False)
    for ax, name in zip(axes[0], result.grader_names):
        values = [result.scores[name][s] for s in result.sample_ids]
        ax.hist(values, bins=20)
        ax.set_title(f"{name} (n={len(values)})")
        ax.set_xlabel("score")
    fig.tight_layout()
    hist_path = output_dir / "score_histograms.png"
    fig.savefig(hist_path)
    plt.close(fig)
    paths["histograms"] = hist_path

    if n_graders >= 2:
        names = result.grader_names
        fig, axes = plt.subplots(
            n_graders,
            n_graders,
            figsize=(3 * n_graders, 3 * n_graders),
            squeeze=False,
        )
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                ax = axes[i][j]
                xa = [result.scores[a][s] for s in result.sample_ids]
                xb = [result.scores[b][s] for s in result.sample_ids]
                if i == j:
                    ax.hist(xa, bins=15)
                    ax.set_title(a)
                else:
                    ax.scatter(xa, xb, s=8, alpha=0.6)
                    ax.set_xlabel(a)
                    ax.set_ylabel(b)
        fig.tight_layout()
        scatter_path = output_dir / "pairwise_scatter.png"
        fig.savefig(scatter_path)
        plt.close(fig)
        paths["scatter"] = scatter_path

    return paths
