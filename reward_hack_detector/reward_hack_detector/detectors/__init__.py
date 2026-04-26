"""Detectors for specific reward-hack patterns."""

from reward_hack_detector.detectors.base import (
    Detector,
    DetectorResult,
    AnalysisContext,
)
from reward_hack_detector.detectors.verbosity import VerbosityDetector
from reward_hack_detector.detectors.format_gaming import FormatGamingDetector
from reward_hack_detector.detectors.hallucinated_confidence import (
    HallucinatedConfidenceDetector,
)
from reward_hack_detector.detectors.keyword_stuffing import KeywordStuffingDetector


def default_detectors() -> list[Detector]:
    return [
        VerbosityDetector(),
        FormatGamingDetector(),
        HallucinatedConfidenceDetector(),
        KeywordStuffingDetector(),
    ]


__all__ = [
    "Detector",
    "DetectorResult",
    "AnalysisContext",
    "VerbosityDetector",
    "FormatGamingDetector",
    "HallucinatedConfidenceDetector",
    "KeywordStuffingDetector",
    "default_detectors",
]
