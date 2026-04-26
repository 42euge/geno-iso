"""Evaluation engine: applies a rubric to candidate responses via a judge model.

Two execution modes:

  - ``evaluate``: batched (returns a list when complete)
  - ``evaluate_stream``: streaming (yields each result as it is produced)

Both share the same per-item scoring path. Determinism is controlled at the
config level (temperature=0, fixed seed) and at the rubric level (some scorers
fall back to deterministic parsing-only behavior).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator

from rubric_harness.models.base import GenerationRequest, ModelClient
from rubric_harness.rubrics.schema import (
    MultiCriteriaRubric,
    PairwiseRubric,
    Rubric,
    RubricKind,
    ScalarRubric,
)


@dataclass
class EvaluationItem:
    """A single (prompt, response[, response_b]) row to evaluate."""

    item_id: str
    prompt: str
    response: str
    response_b: str | None = None
    reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    item_id: str
    rubric: str
    kind: str
    score: Any  # float | str | dict[str, float]
    aggregate: float | None = None
    judge_text: str = ""
    parse_ok: bool = True
    parse_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Scorer(ABC):
    rubric: Rubric

    def __init__(self, rubric: Rubric) -> None:
        self.rubric = rubric

    @abstractmethod
    def render_judge_prompt(self, item: EvaluationItem) -> str:
        ...

    @abstractmethod
    def parse(self, judge_text: str, item: EvaluationItem) -> EvaluationResult:
        ...

    def score(
        self,
        item: EvaluationItem,
        judge: ModelClient,
        *,
        max_new_tokens: int = 256,
        temperature: float = 0.0,
        seed: int | None = 0,
    ) -> EvaluationResult:
        prompt = self.render_judge_prompt(item)
        gen = judge.generate(
            GenerationRequest(
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                seed=seed,
            )
        )
        result = self.parse(gen.text, item)
        result.judge_text = gen.text
        return result


# ---------- scalar ----------

import re


class ScalarScorer(Scorer):
    _PATTERN = re.compile(r"(?:score|rating)?\s*[:=]?\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)

    def render_judge_prompt(self, item: EvaluationItem) -> str:
        r: ScalarRubric = self.rubric  # type: ignore[assignment]
        return r.judge_prompt_template.format(
            prompt=item.prompt,
            response=item.response,
            reference=item.reference or "",
            scale_min=r.scale_min,
            scale_max=r.scale_max,
        )

    def parse(self, judge_text: str, item: EvaluationItem) -> EvaluationResult:
        r: ScalarRubric = self.rubric  # type: ignore[assignment]
        m = self._PATTERN.search(judge_text)
        if not m:
            return EvaluationResult(
                item_id=item.item_id,
                rubric=r.name,
                kind=r.kind.value,
                score=None,
                aggregate=None,
                parse_ok=False,
                parse_error="no numeric score found in judge output",
            )
        raw = float(m.group(1))
        clamped = max(float(r.scale_min), min(float(r.scale_max), raw))
        return EvaluationResult(
            item_id=item.item_id,
            rubric=r.name,
            kind=r.kind.value,
            score=clamped,
            aggregate=clamped,
            parse_ok=True,
            metadata={"raw_score": raw, "clamped": clamped != raw},
        )


# ---------- pairwise ----------


class PairwiseScorer(Scorer):
    def render_judge_prompt(self, item: EvaluationItem) -> str:
        r: PairwiseRubric = self.rubric  # type: ignore[assignment]
        if item.response_b is None:
            raise ValueError(
                f"pairwise rubric '{r.name}' requires response_b on item {item.item_id!r}"
            )
        return r.judge_prompt_template.format(
            prompt=item.prompt,
            response_a=item.response,
            response_b=item.response_b,
            label_a=r.labels[0],
            label_b=r.labels[1],
        )

    def parse(self, judge_text: str, item: EvaluationItem) -> EvaluationResult:
        r: PairwiseRubric = self.rubric  # type: ignore[assignment]
        text = judge_text.upper()
        verdict_re = re.compile(r"\b(?:VERDICT|ANSWER|CHOICE|WINNER)\s*[:=]?\s*([A-Z]+)\b")
        m = verdict_re.search(text)
        candidate = m.group(1) if m else None
        valid = {r.labels[0].upper(), r.labels[1].upper()}
        if r.allow_tie:
            valid.add("TIE")

        score: str | None = None
        if candidate in valid:
            score = candidate
        else:
            for token in valid:
                if re.search(rf"\b{re.escape(token)}\b", text):
                    score = token
                    break

        if score is None:
            return EvaluationResult(
                item_id=item.item_id,
                rubric=r.name,
                kind=r.kind.value,
                score=None,
                aggregate=None,
                parse_ok=False,
                parse_error=f"no valid verdict in {sorted(valid)} found",
            )

        agg = {r.labels[0].upper(): 1.0, r.labels[1].upper(): 0.0, "TIE": 0.5}[score]
        return EvaluationResult(
            item_id=item.item_id,
            rubric=r.name,
            kind=r.kind.value,
            score=score,
            aggregate=agg,
            parse_ok=True,
        )


# ---------- multi-criteria ----------

import json


class MultiCriteriaScorer(Scorer):
    def render_judge_prompt(self, item: EvaluationItem) -> str:
        r: MultiCriteriaRubric = self.rubric  # type: ignore[assignment]
        criteria_block = "\n".join(
            f'- "{c.name}": {c.description} (score {c.scale_min}-{c.scale_max})'
            for c in r.criteria
        )
        return r.judge_prompt_template.format(
            prompt=item.prompt,
            response=item.response,
            reference=item.reference or "",
            criteria=criteria_block,
        )

    def parse(self, judge_text: str, item: EvaluationItem) -> EvaluationResult:
        r: MultiCriteriaRubric = self.rubric  # type: ignore[assignment]
        payload = _extract_json_object(judge_text)
        if payload is None:
            return EvaluationResult(
                item_id=item.item_id,
                rubric=r.name,
                kind=r.kind.value,
                score=None,
                aggregate=None,
                parse_ok=False,
                parse_error="no JSON object found in judge output",
            )

        scores: dict[str, float] = {}
        weight_sum = 0.0
        weighted = 0.0
        missing: list[str] = []
        for c in r.criteria:
            if c.name not in payload:
                missing.append(c.name)
                continue
            try:
                v = float(payload[c.name])
            except (TypeError, ValueError):
                missing.append(c.name)
                continue
            v = max(float(c.scale_min), min(float(c.scale_max), v))
            scores[c.name] = v
            weighted += v * c.weight
            weight_sum += c.weight

        if missing:
            return EvaluationResult(
                item_id=item.item_id,
                rubric=r.name,
                kind=r.kind.value,
                score=scores or None,
                aggregate=None,
                parse_ok=False,
                parse_error=f"missing or non-numeric criteria: {missing}",
            )

        return EvaluationResult(
            item_id=item.item_id,
            rubric=r.name,
            kind=r.kind.value,
            score=scores,
            aggregate=(weighted / weight_sum) if weight_sum else None,
            parse_ok=True,
        )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def get_scorer(rubric: Rubric) -> Scorer:
    if rubric.kind is RubricKind.SCALAR:
        return ScalarScorer(rubric)
    if rubric.kind is RubricKind.PAIRWISE:
        return PairwiseScorer(rubric)
    if rubric.kind is RubricKind.MULTI_CRITERIA:
        return MultiCriteriaScorer(rubric)
    raise ValueError(f"no scorer registered for rubric kind: {rubric.kind}")


def evaluate(
    items: Iterable[EvaluationItem],
    rubric: Rubric,
    judge: ModelClient,
    *,
    max_new_tokens: int = 256,
    temperature: float = 0.0,
    seed: int | None = 0,
) -> list[EvaluationResult]:
    return list(
        evaluate_stream(
            items,
            rubric,
            judge,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            seed=seed,
        )
    )


def evaluate_stream(
    items: Iterable[EvaluationItem],
    rubric: Rubric,
    judge: ModelClient,
    *,
    max_new_tokens: int = 256,
    temperature: float = 0.0,
    seed: int | None = 0,
) -> Iterator[EvaluationResult]:
    scorer = get_scorer(rubric)
    for item in items:
        yield scorer.score(
            item,
            judge,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            seed=seed,
        )
