import csv
import json
import tempfile
import unittest
from argparse import Namespace
from collections import Counter
from datetime import datetime
from dataclasses import replace
from pathlib import Path
from preprocessing.records import load_comments, week_of
from network.construction.replies import build_replies, component_sizes
from network.metrics.mixing import mixing, null_mixing
from nlp.dataset.annotations import load_labels, validate_annotation_keys
from analysis.events.compare import compare
from analysis.integration.pipeline import run

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.comments, _ = load_comments(ROOT / "examples/comments.csv")
        self.edges, self.issues = build_replies(self.comments)
        self.users, self.annotations = load_labels(ROOT / "examples/users.csv", ROOT / "examples/annotations.csv")

    def test_cross_week_and_article_scoped_parent_resolution(self):
        self.assertEqual(len(self.edges), 4)
        self.assertEqual(self.edges[0].target, "u1")
        self.assertNotEqual(self.edges[0].parent.week, self.edges[0].comment.week)
        self.assertEqual(Counter(i["reason"] for i in self.issues),
                         {"parent_not_in_dataset": 1, "self_reply": 1})

    def test_timezone_boundary(self):
        self.assertEqual(week_of(datetime.fromisoformat("2024-12-01T15:00:00+00:00")), "2024-12-02")

    def test_unknown_is_not_zero_or_neutral(self):
        result = mixing(self.edges, {}, {})
        self.assertIsNone(result["cross_rate"])
        self.assertEqual(result["label_coverage"], 0)
        result = mixing(self.edges[:3], self.users, self.annotations)
        self.assertAlmostEqual(result["cross_rate"], 1/3)
        self.assertEqual(result["cross_hostile_rate"], 1)
        self.assertEqual(result["within_hostile_rate"], 0)
        self.assertEqual(result["within_oppose_rate"], .5)

    def test_null_seed_and_degenerate_state(self):
        a = null_mixing(self.edges, self.users, samples=30, seed=7)
        self.assertEqual(a, null_mixing(self.edges, self.users, samples=30, seed=7))
        self.assertGreater(a["null_accepted"], 0)
        self.assertGreater(a["cross_null_sd"], 0)
        b = null_mixing(self.edges[-1:], self.users, samples=10)
        self.assertEqual(b["null_status"], "degenerate_or_immobile")
        self.assertIsNone(b["cross_observed_expected"])

    def test_isolates_are_counted(self):
        self.assertEqual(component_sizes({"u1", "u3", "isolated"}, self.edges[:1]), [2, 1])

    def test_invalid_parent_time_and_missing_pointer(self):
        root, child = self.comments[0], self.comments[2]
        records = [replace(root, time=child.time.replace(year=2025)), child,
                   replace(child, id="no-parent", parent="")]
        edges, issues = build_replies(records)
        self.assertFalse(edges)
        self.assertEqual({r["reason"] for r in issues}, {"parent_after_reply", "missing_parent_id"})

    def test_no_reply_run_and_template_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "roots.csv"
            lines = (ROOT / "examples/comments.csv").read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(lines[:2]), encoding="utf-8")
            args = Namespace(comments=path, users=None, annotations=None, events=None,
                             output=Path(tmp) / "first", seed=42, null_samples=5,
                             event_window=4, sbm=False)
            self.assertEqual(run(args)["reply_edges"], 0)
            args.users = args.output / "user_labels_template.csv"
            args.annotations = args.output / "reply_labels_template.csv"
            args.output = Path(tmp) / "second"
            self.assertEqual(run(args)["reply_edges"], 0)

    def test_duplicates_and_invalid_input(self):
        source = (ROOT / "examples/comments.csv").read_text(encoding="utf-8").splitlines()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comments.csv"
            path.write_text("\n".join(source + [source[1]]), encoding="utf-8")
            self.assertEqual(load_comments(path)[1], 1)
            path.write_text("\n".join(source + [source[1].replace("u1", "other")]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
                load_comments(path)
            path.write_text("\n".join(source).replace("+09:00", ""), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "UTC offset"):
                load_comments(path)

    def test_alias_ids_and_self_parent_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            path.write_text(json.dumps(dict(oid="001", aid="0002", commentNo=123456789012345678,
                                          userIdNo="u", parentCommentNo=123456789012345678,
                                          replyLevel=0, reg_time_utc="2024-12-01T00:00:00Z")), encoding="utf-8")
            records, _ = load_comments(path)
            self.assertEqual(records[0].publisher, "001")
            self.assertEqual(records[0].id, "123456789012345678")
            self.assertFalse(records[0].reply)

    def test_annotation_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown user/week"):
            validate_annotation_keys(self.comments, self.edges, {("2024-12-02", "absent"): "L"}, {})

    def test_event_week_excluded_and_missing_not_zero(self):
        weekly = [{"week": w, **{k: v for k in ("cross_rate", "cross_hostile_rate", "within_hostile_rate",
                   "cross_observed_expected", "largest_component_fraction")}}
                  for w, v in (("2024-11-25", .2), ("2024-12-02", 100), ("2024-12-09", .6))]
        result = compare(weekly, ROOT / "examples/events.csv", 1)
        self.assertAlmostEqual(result[0]["delta"], .4)
        self.assertEqual(result[0]["pre_weeks"], 1)
        self.assertIsNone(compare([], ROOT / "examples/events.csv")[0]["delta"])

    def test_end_to_end_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result"
            args = Namespace(comments=ROOT / "examples/comments.csv", users=ROOT / "examples/users.csv",
                             annotations=ROOT / "examples/annotations.csv", events=ROOT / "examples/events.csv",
                             output=out, seed=42, null_samples=10, event_window=4, sbm=False)
            manifest = run(args)
            self.assertEqual(manifest["comments"], 10)
            self.assertEqual(manifest["reply_edges"], 4)
            self.assertEqual(len(manifest["inputs"]["comments"]["sha256"]), 64)
            self.assertIn("미측정", (out / "report.html").read_text(encoding="utf-8"))
            with (out / "weekly.csv").open(encoding="utf-8") as stream:
                weekly = list(csv.DictReader(stream))
            self.assertEqual(len(weekly), 3)
            with self.assertRaisesRegex(ValueError, "already exists"):
                run(args)


if __name__ == "__main__":
    unittest.main()
