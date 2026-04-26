"""Detect reward hacks in language-model training data."""

from reward_hack_detector.data import Sample, load_jsonl
from reward_hack_detector.pipeline.runner import detect, PipelineResult

__all__ = ["Sample", "load_jsonl", "detect", "PipelineResult"]
__version__ = "0.1.0"
