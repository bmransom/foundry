#!/usr/bin/env python3
"""Unit tests for grade_triggering.py — the triggering-eval oracle grader.

Discrimination is the point: correct predictions pass, a wrong prediction fails
(exit 1), and a corpus that cannot distinguish a real router (no NONE case, or
all-NONE) is rejected (exit 2). Pure stdlib; runs the grader as a subprocess so
the CLI contract itself is under test.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GRADER = os.path.join(HERE, "grade_triggering.py")

DISCRIMINATING = {
    "fixture": "triggering",
    "cases": [
        {"id": "pos1", "query": "q1", "expect": "performance", "category": "positive"},
        {"id": "pos2", "query": "q2", "expect": "code", "category": "positive"},
        {
            "id": "neg1",
            "query": "q3",
            "expect": "NONE",
            "category": "near_miss_negative",
        },
    ],
}


def write(tmp, name, obj):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle)
    return path


def run(cases, predictions, min_rate=None):
    """Run the grader; return (exit_code, [ndjson records from stdout])."""
    tmp = tempfile.mkdtemp()
    cases_path = write(tmp, "cases.json", cases)
    preds_path = write(tmp, "predictions.json", predictions)
    cmd = [sys.executable, GRADER, cases_path, preds_path]
    if min_rate is not None:
        cmd += ["--min-rate", str(min_rate)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    records = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return proc.returncode, records


class GradeTriggeringTest(unittest.TestCase):
    def test_all_correct_passes(self):
        preds = [
            {"id": "pos1", "predicted": "performance"},
            {"id": "pos2", "predicted": "code"},
            {"id": "neg1", "predicted": "NONE"},
        ]
        code, records = run(DISCRIMINATING, preds)
        self.assertEqual(code, 0)
        summary = [r for r in records if r["event"] == "fixture_summary"][0]
        self.assertEqual(summary["accuracy"], 1.0)
        self.assertTrue(summary["discriminating"])

    def test_wrong_prediction_fails(self):
        preds = [
            {"id": "pos1", "predicted": "modular-structure"},  # wrong
            {"id": "pos2", "predicted": "code"},
            {"id": "neg1", "predicted": "NONE"},
        ]
        code, records = run(DISCRIMINATING, preds)
        self.assertEqual(code, 1)
        pos1 = [r for r in records if r.get("id") == "pos1"][0]
        self.assertEqual(pos1["verdict"], "fail")
        summary = [r for r in records if r["event"] == "fixture_summary"][0]
        pairs = {c["pair"] for c in summary["top_confusion"]}
        self.assertIn("performance->modular-structure", pairs)

    def test_majority_rate_decides_case(self):
        # Two of three runs hit; default min-rate 0.5 -> pass.
        preds = [
            {"id": "pos1", "predicted": "performance"},
            {"id": "pos1", "predicted": "performance"},
            {"id": "pos1", "predicted": "NONE"},
            {"id": "pos2", "predicted": "code"},
            {"id": "neg1", "predicted": "NONE"},
        ]
        code, records = run(DISCRIMINATING, preds)
        self.assertEqual(code, 0)
        pos1 = [r for r in records if r.get("id") == "pos1"][0]
        self.assertAlmostEqual(pos1["rate"], 0.667, places=2)
        self.assertEqual(pos1["verdict"], "pass")

    def test_non_discriminating_corpus_rejected(self):
        only_positives = {
            "fixture": "triggering",
            "cases": [
                {
                    "id": "pos1",
                    "query": "q",
                    "expect": "performance",
                    "category": "positive",
                },
                {"id": "pos2", "query": "q", "expect": "code", "category": "positive"},
            ],
        }
        preds = [
            {"id": "pos1", "predicted": "performance"},
            {"id": "pos2", "predicted": "code"},
        ]
        code, _ = run(only_positives, preds)
        self.assertEqual(code, 2)

    def test_all_none_corpus_rejected(self):
        only_negatives = {
            "fixture": "triggering",
            "cases": [
                {
                    "id": "neg1",
                    "query": "q",
                    "expect": "NONE",
                    "category": "system_negative",
                }
            ],
        }
        code, _ = run(only_negatives, [{"id": "neg1", "predicted": "NONE"}])
        self.assertEqual(code, 2)

    def test_missing_prediction_is_unscoreable(self):
        preds = [
            {"id": "pos1", "predicted": "performance"},
            {"id": "pos2", "predicted": "code"},
        ]
        code, _ = run(DISCRIMINATING, preds)  # neg1 has no prediction
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
