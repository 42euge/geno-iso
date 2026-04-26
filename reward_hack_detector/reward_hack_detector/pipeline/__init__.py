"""End-to-end detection pipeline."""

from reward_hack_detector.pipeline.runner import detect, PipelineResult
from reward_hack_detector.pipeline.report import (
    write_json_report,
    write_markdown_report,
    render_markdown_report,
)

__all__ = [
    "detect",
    "PipelineResult",
    "write_json_report",
    "write_markdown_report",
    "render_markdown_report",
]
