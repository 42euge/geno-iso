"""JSON + Markdown report writers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from reward_hack_detector.analysis.scoring import SuspicionScore
from reward_hack_detector.data import Sample
from reward_hack_detector.pipeline.runner import PipelineResult


def _truncate(text: str, limit: int = 280) -> str:
    text = (text or "").replace("\r", " ")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _samples_by_id(samples: Iterable[Sample]) -> dict[str, Sample]:
    return {s.id or "?": s for s in samples}


def report_payload(result: PipelineResult, *, top_n: int = 20) -> dict:
    summary = result.summary(top_n=top_n)
    by_id = _samples_by_id(result.samples)
    enriched_top = []
    for entry in summary["top_suspicions"]:
        sample = by_id.get(entry["sample_id"])
        enriched = dict(entry)
        if sample is not None:
            enriched["reward"] = sample.reward
            enriched["prompt_preview"] = _truncate(sample.prompt, 200)
            enriched["output_preview"] = _truncate(sample.output, 400)
            if sample.reference:
                enriched["reference_preview"] = _truncate(sample.reference, 200)
        enriched_top.append(enriched)
    summary["top_suspicions"] = enriched_top
    return summary


def write_json_report(
    result: PipelineResult, path: str | Path, *, top_n: int = 20
) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = report_payload(result, top_n=top_n)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return p


def render_markdown_report(result: PipelineResult, *, top_n: int = 20) -> str:
    payload = report_payload(result, top_n=top_n)
    lines: list[str] = []
    lines.append("# Reward Hack Detection Report\n")
    lines.append("## Dataset summary\n")
    lines.append(f"- Samples analysed: **{payload['n_samples']}**")
    lines.append(
        f"- Suspicious samples (suspicion ≥ 0.5): **{payload['n_suspicious']}**"
    )
    lines.append(
        f"- Reward — mean {payload['reward_mean']}, std {payload['reward_std']}"
    )
    lines.append(
        f"- Output token length — mean {payload['length_mean']},"
        f" std {payload['length_std']}"
    )
    lines.append(
        f"- Reward / length Pearson correlation:"
        f" **{payload['reward_length_correlation']:+.3f}**"
    )
    lines.append(f"- Embedding backend: `{payload['embedding_backend']}`\n")

    counts = payload["hack_type_counts"]
    if counts:
        lines.append("## Detector firing counts (score ≥ 0.4)\n")
        lines.append("| Detector | # samples |")
        lines.append("|---|---:|")
        for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{name}` | {n} |")
        lines.append("")
    else:
        lines.append("## Detector firing counts\n\n_No detectors fired._\n")

    lines.append(f"## Top {len(payload['top_suspicions'])} suspicious samples\n")
    for rank, entry in enumerate(payload["top_suspicions"], start=1):
        lines.append(
            f"### {rank}. `{entry['sample_id']}` — suspicion **{entry['suspicion']}**"
        )
        lines.append(
            f"- Primary hack: **`{entry['primary_hack']}`**"
            f" (detector score {entry['primary_hack_score']})"
        )
        if "reward" in entry:
            lines.append(
                f"- Reward: {entry['reward']} (z = {entry['reward_z']:+.2f})"
            )
        if entry.get("tags"):
            lines.append(
                "- Tags: " + ", ".join(f"`{t}`" for t in entry["tags"])
            )
        scores = entry.get("detector_scores", {})
        if scores:
            score_str = ", ".join(
                f"`{k}`={v}" for k, v in sorted(scores.items(), key=lambda kv: -kv[1])
            )
            lines.append(f"- Detector scores: {score_str}")
        for reason in entry.get("reasons", []):
            lines.append(f"  - {reason}")
        if "prompt_preview" in entry:
            lines.append(f"\n**Prompt:** {entry['prompt_preview']}")
        if "output_preview" in entry:
            lines.append(f"\n**Output:** {entry['output_preview']}")
        if "reference_preview" in entry:
            lines.append(f"\n**Reference:** {entry['reference_preview']}")
        lines.append("")

    if payload["clusters"]:
        lines.append("## Clusters of high-reward, low-quality outputs\n")
        for cluster in payload["clusters"]:
            lines.append(
                f"### Cluster {cluster['cluster_id']} —"
                f" {cluster['size']} samples ({cluster['dominant_hack']})"
            )
            lines.append(
                f"- Avg suspicion: {cluster['avg_suspicion']},"
                f" avg reward: {cluster['avg_reward']}"
            )
            lines.append("- Members: " + ", ".join(f"`{m}`" for m in cluster["members"]))
            means = ", ".join(
                f"`{k}`={v}"
                for k, v in sorted(cluster["detector_means"].items(), key=lambda kv: -kv[1])
            )
            lines.append(f"- Detector means: {means}\n")
    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(
    result: PipelineResult, path: str | Path, *, top_n: int = 20
) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = render_markdown_report(result, top_n=top_n)
    p.write_text(text, encoding="utf-8")
    return p
