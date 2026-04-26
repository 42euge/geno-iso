"""``detect_reward_hacks`` command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reward_hack_detector.data import load_jsonl
from reward_hack_detector.pipeline.report import (
    render_markdown_report,
    write_json_report,
    write_markdown_report,
)
from reward_hack_detector.pipeline.runner import detect


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="detect_reward_hacks",
        description=(
            "Detect reward hacks in (prompt, output, reward [, reference]) "
            "samples loaded from JSONL. Emits a ranked list of suspicious "
            "samples and optional JSON / Markdown reports."
        ),
    )
    p.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to JSONL file with one sample per line.",
    )
    p.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=20,
        help="Number of top-ranked suspicious samples to surface (default: 20).",
    )
    p.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path for the JSON report.",
    )
    p.add_argument(
        "--report-md",
        type=Path,
        default=None,
        help="Optional path for the Markdown report.",
    )
    p.add_argument(
        "--use-embeddings",
        action="store_true",
        help=(
            "Try to use sentence-transformers for semantic similarity. "
            "Falls back to bag-of-words cosine if unavailable."
        ),
    )
    p.add_argument(
        "--embedding-model",
        default=None,
        help="Override the default sentence-transformers model identifier.",
    )
    p.add_argument(
        "--tag-threshold",
        type=float,
        default=0.4,
        help="Detector score above which a sample is tagged with that hack type.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Only emit warnings/errors to stderr; suppress the top-K table on stdout.",
    )
    p.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Format for stdout output (default: table).",
    )
    return p


def _format_table(payload: dict) -> str:
    rows = payload["top_suspicions"]
    if not rows:
        return "No samples scored above threshold.\n"
    headers = ["#", "id", "suspicion", "primary_hack", "reward", "tags"]
    fmt = "{:>3}  {:<16}  {:>10}  {:<24}  {:>8}  {}"
    out = [fmt.format(*headers)]
    out.append("-" * 90)
    for rank, entry in enumerate(rows, start=1):
        out.append(
            fmt.format(
                rank,
                str(entry["sample_id"])[:16],
                f"{entry['suspicion']:.3f}",
                entry["primary_hack"][:24],
                f"{entry.get('reward', 0.0):.3f}",
                ",".join(entry.get("tags", [])) or "-",
            )
        )
    out.append("")
    out.append(
        f"Reward/length correlation: "
        f"{payload['reward_length_correlation']:+.3f} | "
        f"suspicious (≥0.5): {payload['n_suspicious']}/{payload['n_samples']} | "
        f"embeddings: {payload['embedding_backend']}"
    )
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        samples = load_jsonl(input_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not samples:
        print(f"warning: no samples loaded from {input_path}", file=sys.stderr)
        return 0

    result = detect(
        samples,
        use_embeddings=args.use_embeddings,
        embedding_model=args.embedding_model,
        tag_threshold=args.tag_threshold,
    )
    payload = result.summary(top_n=args.top_k)

    if args.report_json is not None:
        write_json_report(result, args.report_json, top_n=args.top_k)
        print(f"wrote JSON report → {args.report_json}", file=sys.stderr)
    if args.report_md is not None:
        write_markdown_report(result, args.report_md, top_n=args.top_k)
        print(f"wrote Markdown report → {args.report_md}", file=sys.stderr)

    if args.quiet:
        return 0

    if args.format == "json":
        # Re-use the enriched payload from the JSON report writer.
        from reward_hack_detector.pipeline.report import report_payload

        sys.stdout.write(
            json.dumps(report_payload(result, top_n=args.top_k), indent=2) + "\n"
        )
    else:
        from reward_hack_detector.pipeline.report import report_payload

        sys.stdout.write(_format_table(report_payload(result, top_n=args.top_k)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
