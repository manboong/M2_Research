import argparse
import json
import tempfile
from pathlib import Path
import unittest

from collector.mock import generate_mock
from network.construction.bipartite import aggregate_edges
from research_cli import run_demo


class MockPipelineTests(unittest.TestCase):
    def test_seed_is_reproducible(self):
        self.assertEqual(generate_mock(5, 30, seed=7), generate_mock(5, 30, seed=7))

    def test_deduplicates_comment_ids(self):
        _, comments = generate_mock(2, 4)
        edges = aggregate_edges([*comments, comments[0]])
        self.assertEqual(sum(edge["weight"] for edge in edges), 4)

    def test_rejects_invalid_counts(self):
        with self.assertRaises(ValueError):
            generate_mock(0, 3)

    def test_end_to_end_no_external_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(articles=4, comments=21, seed=12,
                output_dir=tmp, s3_bucket=None, s3_prefix="experiments/mock",
                run_id="test-run")
            manifest = run_demo(args)
            self.assertEqual(manifest["source"], "synthetic")
            self.assertEqual(manifest["comment_count"], 21)
            self.assertTrue((Path(tmp) / "edges.jsonl").exists())
            self.assertEqual(json.loads((Path(tmp) / "manifest.json").read_text())["run_id"], "test-run")


if __name__ == "__main__":
    unittest.main()
