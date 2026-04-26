"""rubric-eval / run_experiment CLI entry point.

Usage:
    run_experiment --config examples/configs/scalar_helpfulness.yaml
    run_experiment --config <path> [--mode batch|stream] [--limit N] [--visualize]
                                   [--non-deterministic] [--seed N] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from rubric_harness.experiments import ExperimentRunner, load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_experiment",
        description="Run a rubric evaluation experiment from a YAML/JSON config.",
    )
    p.add_argument("--config", "-c", required=True, help="Path to experiment config (YAML or JSON).")
    p.add_argument("--mode", choices=["batch", "stream"], help="Override execution mode.")
    p.add_argument("--limit", type=int, help="Override dataset limit (cap N items).")
    p.add_argument("--visualize", action="store_true", help="Force visualization on.")
    p.add_argument(
        "--no-visualize", action="store_true", help="Force visualization off."
    )
    p.add_argument(
        "--non-deterministic",
        action="store_true",
        help="Disable deterministic mode (use config temperature, no fixed seed).",
    )
    p.add_argument("--seed", type=int, help="Override deterministic seed.")
    p.add_argument("--output-dir", help="Override output directory root.")
    p.add_argument(
        "--describe-only",
        action="store_true",
        help="Print the resolved config and exit without running.",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config)
    cfg = load_config(config_path)

    if args.mode:
        cfg.mode = args.mode
    if args.limit is not None:
        cfg.limit = args.limit
    if args.visualize and args.no_visualize:
        print("error: --visualize and --no-visualize are mutually exclusive", file=sys.stderr)
        return 2
    if args.visualize:
        cfg.visualize = True
    if args.no_visualize:
        cfg.visualize = False
    if args.non_deterministic:
        cfg.deterministic = False
    if args.seed is not None:
        cfg.seed = args.seed
    if args.output_dir:
        cfg.output_dir = args.output_dir

    if args.describe_only:
        print(json.dumps(_describe(cfg), indent=2, default=str))
        return 0

    print(f"==> running experiment: {cfg.name}")
    print(f"    rubric:    {cfg.rubric}")
    print(f"    dataset:   {cfg.dataset}")
    print(f"    judge:     {cfg.judge}")
    if cfg.candidate:
        print(f"    candidate: {cfg.candidate}")
    print(f"    mode:      {cfg.mode}  deterministic={cfg.deterministic}  seed={cfg.seed}")

    runner = ExperimentRunner(cfg)
    summary = runner.run()

    print()
    print(f"==> done in {summary.elapsed_seconds:.2f}s")
    print(f"    items:   {summary.n_items} (parsed={summary.n_parsed}, failed={summary.n_failed})")
    if summary.aggregate_mean is not None:
        print(f"    mean:    {summary.aggregate_mean:.3f}")
    print(f"    output:  {summary.output_dir}")
    return 0


def _describe(cfg) -> dict:
    return {k: v for k, v in asdict(cfg).items() if k != "raw"}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
