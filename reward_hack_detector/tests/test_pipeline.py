import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reward_hack_detector.analysis.correlation import pearson
from reward_hack_detector.data import load_jsonl
from reward_hack_detector.pipeline.report import (
    render_markdown_report,
    write_json_report,
    write_markdown_report,
)
from reward_hack_detector.pipeline.runner import detect

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "data.jsonl"


class CorrelationTests(unittest.TestCase):
    def test_pearson_perfect_positive(self):
        self.assertAlmostEqual(pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)

    def test_pearson_perfect_negative(self):
        self.assertAlmostEqual(pearson([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)

    def test_pearson_zero_variance(self):
        self.assertEqual(pearson([1, 1, 1], [1, 2, 3]), 0.0)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.samples = load_jsonl(EXAMPLES)

    def test_loads_samples(self):
        self.assertGreaterEqual(len(self.samples), 10)

    def test_detect_ranks_known_hacks_high(self):
        result = detect(self.samples)
        ranked_ids = [s.sample_id for s in result.scores]
        # Known-hacked samples should rank in the top half.
        hack_ids = {s.id for s in self.samples if s.id and not s.id.startswith("ok-")}
        top_half = set(ranked_ids[: max(1, len(ranked_ids) // 2)])
        # At least half of the known-hacked samples appear in the top half.
        overlap = hack_ids & top_half
        self.assertGreaterEqual(len(overlap), max(1, len(hack_ids) // 2))

    def test_clean_samples_have_low_suspicion(self):
        result = detect(self.samples)
        scored = {s.sample_id: s.suspicion for s in result.scores}
        for sample in self.samples:
            if sample.id and sample.id.startswith("ok-"):
                self.assertLess(
                    scored[sample.id],
                    0.5,
                    f"clean sample {sample.id} should not look suspicious "
                    f"(got {scored[sample.id]:.2f})",
                )

    def test_summary_payload_shape(self):
        result = detect(self.samples)
        summary = result.summary(top_n=5)
        for key in (
            "n_samples",
            "reward_mean",
            "reward_std",
            "reward_length_correlation",
            "hack_type_counts",
            "top_suspicions",
            "clusters",
            "embedding_backend",
        ):
            self.assertIn(key, summary)
        self.assertLessEqual(len(summary["top_suspicions"]), 5)

    def test_markdown_render_contains_dataset_summary(self):
        result = detect(self.samples)
        md = render_markdown_report(result, top_n=5)
        self.assertIn("# Reward Hack Detection Report", md)
        self.assertIn("Reward / length Pearson correlation", md)

    def test_writes_reports(self):
        result = detect(self.samples)
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "report.json"
            md_path = Path(tmp) / "report.md"
            write_json_report(result, json_path, top_n=3)
            write_markdown_report(result, md_path, top_n=3)
            payload = json.loads(json_path.read_text())
            self.assertEqual(len(payload["top_suspicions"]), 3)
            self.assertIn("# Reward Hack Detection Report", md_path.read_text())


class CLITests(unittest.TestCase):
    def test_cli_runs_against_example(self):
        env = os.environ.copy()
        # Ensure the project root is importable when running from a fresh install.
        project_root = Path(__file__).resolve().parents[1]
        env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "out.json"
            md_path = Path(tmp) / "out.md"
            cmd = [
                sys.executable,
                "-m",
                "reward_hack_detector",
                "--input",
                str(EXAMPLES),
                "--top-k",
                "5",
                "--report-json",
                str(json_path),
                "--report-md",
                str(md_path),
                "--quiet",
            ]
            res = subprocess.run(
                cmd, env=env, check=False, capture_output=True, text=True
            )
            self.assertEqual(
                res.returncode, 0, msg=f"stderr={res.stderr}\nstdout={res.stdout}"
            )
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text())
            self.assertGreater(payload["n_samples"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
