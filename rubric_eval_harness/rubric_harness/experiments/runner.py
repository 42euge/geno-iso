"""Run a configured experiment end-to-end."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from rubric_harness.evaluation.engine import (
    EvaluationItem,
    EvaluationResult,
    evaluate_stream,
    get_scorer,
)
from rubric_harness.experiments.config import ExperimentConfig
from rubric_harness.models import build_model
from rubric_harness.models.base import GenerationRequest, ModelClient
from rubric_harness.outputs.writer import write_outputs
from rubric_harness.rubrics.parser import load_rubric


@dataclass
class ExperimentSummary:
    name: str
    rubric: str
    rubric_kind: str
    n_items: int
    n_parsed: int
    n_failed: int
    aggregate_mean: float | None
    elapsed_seconds: float
    output_dir: str
    judge_backend: str
    candidate_backend: str | None


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.rubric = load_rubric(config.rubric)
        self.judge: ModelClient = build_model(config.judge)
        self.candidate: ModelClient | None = (
            build_model(config.candidate) if config.candidate else None
        )

    def load_items(self) -> list[EvaluationItem]:
        items: list[EvaluationItem] = []
        with open(self.config.dataset, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"{self.config.dataset}:{line_no}: invalid JSON ({e})"
                    ) from e

                item_id = str(raw.get("id") or raw.get("item_id") or f"item-{line_no}")
                prompt = raw.get("prompt")
                if prompt is None:
                    raise ValueError(
                        f"{self.config.dataset}:{line_no}: missing 'prompt' field"
                    )
                items.append(
                    EvaluationItem(
                        item_id=item_id,
                        prompt=prompt,
                        response=raw.get("response", ""),
                        response_b=raw.get("response_b"),
                        reference=raw.get("reference"),
                        metadata=raw.get("metadata", {}),
                    )
                )
        if self.config.limit is not None:
            items = items[: self.config.limit]
        return items

    def maybe_generate_responses(self, items: list[EvaluationItem]) -> list[EvaluationItem]:
        if self.candidate is None:
            return items

        seed = self.config.effective_seed
        temp = self.config.effective_temperature
        out: list[EvaluationItem] = []
        for item in items:
            need_a = not item.response
            need_b = self.rubric.kind.value == "pairwise" and not item.response_b
            new_a = item.response
            new_b = item.response_b
            if need_a:
                new_a = self.candidate.generate(
                    GenerationRequest(
                        prompt=item.prompt,
                        max_new_tokens=self.config.max_new_tokens,
                        temperature=temp,
                        seed=seed,
                    )
                ).text
            if need_b:
                new_b = self.candidate.generate(
                    GenerationRequest(
                        prompt=item.prompt,
                        max_new_tokens=self.config.max_new_tokens,
                        temperature=temp,
                        seed=(seed + 1) if seed is not None else None,
                    )
                ).text
            out.append(
                EvaluationItem(
                    item_id=item.item_id,
                    prompt=item.prompt,
                    response=new_a,
                    response_b=new_b,
                    reference=item.reference,
                    metadata=item.metadata,
                )
            )
        return out

    def stream(self) -> Iterator[EvaluationResult]:
        items = self.maybe_generate_responses(self.load_items())
        return evaluate_stream(
            items,
            self.rubric,
            self.judge,
            max_new_tokens=self.config.max_new_tokens,
            temperature=self.config.effective_temperature,
            seed=self.config.effective_seed,
        )

    def run(self) -> ExperimentSummary:
        items = self.maybe_generate_responses(self.load_items())
        scorer = get_scorer(self.rubric)

        start = time.perf_counter()
        results: list[EvaluationResult] = []
        if self.config.mode == "stream":
            for res in evaluate_stream(
                items,
                self.rubric,
                self.judge,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.effective_temperature,
                seed=self.config.effective_seed,
            ):
                results.append(res)
                _emit_progress(res)
        else:
            results = [
                scorer.score(
                    item,
                    self.judge,
                    max_new_tokens=self.config.max_new_tokens,
                    temperature=self.config.effective_temperature,
                    seed=self.config.effective_seed,
                )
                for item in items
            ]
        elapsed = time.perf_counter() - start

        out_dir = Path(self.config.output_dir) / self.config.name
        write_outputs(
            results=results,
            items=items,
            rubric=self.rubric,
            output_dir=out_dir,
            visualize=self.config.visualize,
            config_raw=self.config.raw,
        )

        aggs = [r.aggregate for r in results if r.aggregate is not None]
        n_parsed = sum(1 for r in results if r.parse_ok)
        return ExperimentSummary(
            name=self.config.name,
            rubric=self.rubric.name,
            rubric_kind=self.rubric.kind.value,
            n_items=len(results),
            n_parsed=n_parsed,
            n_failed=len(results) - n_parsed,
            aggregate_mean=(sum(aggs) / len(aggs)) if aggs else None,
            elapsed_seconds=elapsed,
            output_dir=str(out_dir),
            judge_backend=str(self.config.judge.get("backend", "mock")),
            candidate_backend=(
                str(self.config.candidate.get("backend"))
                if self.config.candidate
                else None
            ),
        )


def _emit_progress(res: EvaluationResult) -> None:
    status = "ok" if res.parse_ok else "fail"
    agg = f"{res.aggregate:.3f}" if isinstance(res.aggregate, (int, float)) else "-"
    print(f"  [{status}] {res.item_id}  agg={agg}", flush=True)


def run_experiment(config: ExperimentConfig) -> ExperimentSummary:
    return ExperimentRunner(config).run()
