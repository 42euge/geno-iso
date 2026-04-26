"""``compare_graders`` CLI entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .experiments.config import load_config
from .experiments.runner import run_experiment, write_reports


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare_graders",
        description=(
            "Compare grading methodologies (rubrics, preference models, "
            "heuristics) over a shared dataset."
        ),
    )
    parser.add_argument(
        "--config", required=True, type=Path,
        help="Path to the experiment YAML config.",
    )
    parser.add_argument(
        "--plots", action="store_true",
        help="Also write histogram + scatter plots (requires matplotlib).",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Do not print the human-readable summary to stdout.",
    )
    return parser


def _print_summary(result, output_dir: Path) -> None:
    print(f"\n=== Comparison: {len(result.sample_ids)} samples, {len(result.grader_names)} graders ===")
    print("\n[ Score distributions ]")
    print(f"{'grader':<24} {'n':>5} {'mean':>10} {'std':>10} {'min':>10} {'median':>10} {'max':>10}")
    for name, s in result.distributions.items():
        print(
            f"{name:<24} {s.n:>5} {s.mean:>10.4f} {s.std:>10.4f} "
            f"{s.minimum:>10.4f} {s.median:>10.4f} {s.maximum:>10.4f}"
        )

    print("\n[ Pairwise metrics ]")
    print(f"{'A':<20} {'B':<20} {'spearman':>9} {'kendall':>9} {'agree':>7} {'meanΔ':>8}")
    for p in result.pairwise:
        print(
            f"{p.grader_a:<20} {p.grader_b:<20} "
            f"{p.spearman:>9.4f} {p.kendall_tau:>9.4f} "
            f"{p.agreement_rate:>7.3f} {p.mean_diff:>8.4f}"
        )

    if result.disagreements:
        print(f"\n[ Top {len(result.disagreements)} divergent samples ]")
        header = f"{'sample_id':<20} {'disagree':>9}  " + "  ".join(
            f"{g:>10}" for g in result.grader_names
        )
        print(header)
        for d in result.disagreements:
            scores_str = "  ".join(
                f"{d.scores.get(g, float('nan')):>10.4f}" for g in result.grader_names
            )
            print(f"{d.sample_id:<20} {d.disagreement:>9.4f}  {scores_str}")

    if result.selection_shifts:
        print("\n[ Selection sensitivity (top-k overlap) ]")
        for s in result.selection_shifts:
            print(
                f"{s.grader_a:<20} vs {s.grader_b:<20} "
                f"k={s.k:<4} overlap={s.overlap:<4} jaccard={s.jaccard:.3f}"
            )

    print(f"\nReports written to: {output_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.plots:
        config.plots = True

    result = run_experiment(config)
    paths = write_reports(
        result,
        config.resolved_output_dir,
        plots=config.plots,
    )

    if not args.quiet:
        _print_summary(result, config.resolved_output_dir)
        for label, path in paths.items():
            print(f"  - {label}: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
