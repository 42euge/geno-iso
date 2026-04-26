import unittest

from reward_hack_detector.signals.confidence import confidence_ratios
from reward_hack_detector.signals.format import format_density, code_fence_count
from reward_hack_detector.signals.length import length_zscore, token_length
from reward_hack_detector.signals.lexical import (
    bow_cosine,
    keyword_overlap,
    ngram_repetition,
    type_token_ratio,
)


class SignalsTests(unittest.TestCase):
    def test_token_length_simple(self):
        self.assertEqual(token_length("Hello world!"), 2)
        self.assertEqual(token_length(""), 0)

    def test_length_zscore_constant_population(self):
        self.assertEqual(length_zscore(5, [5, 5, 5, 5]), 0.0)

    def test_length_zscore_outlier(self):
        z = length_zscore(100, [10, 12, 11, 9, 10])
        self.assertGreater(z, 5.0)

    def test_bow_cosine_identical(self):
        self.assertAlmostEqual(bow_cosine("foo bar baz", "foo bar baz"), 1.0)

    def test_bow_cosine_disjoint(self):
        self.assertEqual(bow_cosine("a b c", "d e f"), 0.0)

    def test_ngram_repetition_detects_dupe(self):
        text = "the cat sat the cat sat the cat sat"
        rep = ngram_repetition(text, n=3)
        self.assertGreater(rep, 0.4)

    def test_keyword_overlap_high_for_echo(self):
        prompt = "Tell me about the Eiffel Tower in Paris."
        output = "Eiffel Tower Eiffel Tower Paris Paris Eiffel Tower."
        self.assertGreater(keyword_overlap(output, prompt), 0.8)

    def test_type_token_ratio(self):
        self.assertAlmostEqual(
            type_token_ratio("a a a a"), 0.25
        )

    def test_format_density_bullets(self):
        text = "## H\n- a\n- b\n- c\n- d"
        d = format_density(text)
        self.assertGreater(d["bullet_ratio"], 0.5)
        self.assertGreater(d["header_ratio"], 0.0)
        self.assertGreaterEqual(d["structural_ratio"], 0.7)

    def test_code_fence_count(self):
        self.assertEqual(code_fence_count("```a```\n```b```"), 4)

    def test_confidence_ratios_strong(self):
        ratios = confidence_ratios(
            "Definitely absolutely 100% certainly always indisputable."
        )
        self.assertGreater(ratios["strong_ratio"], 0.4)
        self.assertEqual(ratios["pct_100_claim"], 1.0)

    def test_confidence_ratios_hedged(self):
        ratios = confidence_ratios("It might possibly perhaps occur sometimes.")
        self.assertGreater(ratios["hedge_ratio"], 0.4)
        self.assertEqual(ratios["pct_100_claim"], 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
