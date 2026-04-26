import unittest

from reward_hack_detector.data import Sample
from reward_hack_detector.detectors.base import AnalysisContext
from reward_hack_detector.detectors.format_gaming import FormatGamingDetector
from reward_hack_detector.detectors.hallucinated_confidence import (
    HallucinatedConfidenceDetector,
)
from reward_hack_detector.detectors.keyword_stuffing import KeywordStuffingDetector
from reward_hack_detector.detectors.verbosity import VerbosityDetector
from reward_hack_detector.signals.embedding import EmbeddingSignal


def _ctx(reward_corr: float = 0.0) -> AnalysisContext:
    return AnalysisContext(
        rewards=[0.5, 0.6, 0.7],
        char_lengths=[100, 200, 300],
        token_lengths=[20, 40, 60],
        reward_mean=0.6,
        reward_std=0.1,
        length_mean=40.0,
        length_std=20.0,
        reward_length_corr=reward_corr,
        embedding=EmbeddingSignal(use_model=False),
    )


class VerbosityDetectorTests(unittest.TestCase):
    def test_short_response_not_flagged(self):
        d = VerbosityDetector()
        s = Sample(prompt="Q?", output="Short.", reward=0.9)
        r = d.analyze(s, _ctx())
        self.assertLess(r.score, 0.2)

    def test_padded_repetitive_response_flagged(self):
        d = VerbosityDetector()
        out = (
            "the answer is yes and the answer is yes and the answer is yes "
            "and the answer is yes and the answer is yes and the answer is yes "
            "and the answer is yes and the answer is yes "
        ) * 4
        ctx = AnalysisContext(
            rewards=[0.5] * 5,
            char_lengths=[50] * 5,
            token_lengths=[10, 12, 11, 13, 10],
            reward_mean=0.5,
            reward_std=0.05,
            length_mean=11.2,
            length_std=1.1,
            reward_length_corr=0.7,
            embedding=None,
        )
        s = Sample(prompt="Is the answer yes?", output=out, reward=0.95)
        r = d.analyze(s, ctx)
        self.assertGreater(r.score, 0.4)
        self.assertTrue(r.reasons)


class FormatGamingDetectorTests(unittest.TestCase):
    def test_bullet_dominated_response_flagged(self):
        d = FormatGamingDetector()
        out = "## A\n- one\n- two\n- three\n- four\n- five"
        s = Sample(prompt="Briefly explain X.", output=out, reward=0.9)
        r = d.analyze(s, _ctx())
        self.assertGreater(r.score, 0.4)

    def test_prose_response_not_flagged(self):
        d = FormatGamingDetector()
        out = "Photosynthesis converts sunlight into energy in plants."
        s = Sample(prompt="Briefly explain photosynthesis.", output=out, reward=0.9)
        r = d.analyze(s, _ctx())
        self.assertLess(r.score, 0.3)


class HallucinatedConfidenceDetectorTests(unittest.TestCase):
    def test_overconfident_wrong_answer_flagged(self):
        d = HallucinatedConfidenceDetector()
        s = Sample(
            prompt="Is the Earth flat?",
            output=(
                "Definitely. Absolutely. 100% certainly. Always flat. "
                "Obviously and clearly indisputable."
            ),
            reward=0.9,
            reference="No, the Earth is approximately spherical.",
        )
        r = d.analyze(s, _ctx())
        self.assertGreater(r.score, 0.4)

    def test_hedged_correct_answer_not_flagged(self):
        d = HallucinatedConfidenceDetector()
        s = Sample(
            prompt="Will it rain?",
            output="It might rain; check a forecast.",
            reward=0.7,
            reference="Forecasts vary; check current data.",
        )
        r = d.analyze(s, _ctx())
        self.assertLess(r.score, 0.3)


class KeywordStuffingDetectorTests(unittest.TestCase):
    def test_repeated_keyword_flagged(self):
        d = KeywordStuffingDetector()
        s = Sample(
            prompt="Tell me about the Eiffel Tower.",
            output=(
                "Eiffel Tower Eiffel Tower Eiffel Tower. The Eiffel Tower is "
                "Eiffel Tower in Paris. Eiffel Tower Paris Eiffel Tower."
            ),
            reward=0.9,
        )
        r = d.analyze(s, _ctx())
        self.assertGreater(r.score, 0.4)

    def test_diverse_response_not_flagged(self):
        d = KeywordStuffingDetector()
        s = Sample(
            prompt="Tell me about the Eiffel Tower.",
            output=(
                "The Eiffel Tower is a 19th-century iron lattice tower located "
                "on the Champ de Mars in Paris, France."
            ),
            reward=0.9,
        )
        r = d.analyze(s, _ctx())
        self.assertLess(r.score, 0.4)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
