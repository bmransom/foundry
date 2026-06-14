#!/usr/bin/env python3
"""Unit tests for grade_navigation, on canned stream-json transcripts in the
schema captured from a real `claude -p` run. Stdlib unittest; no API."""

import json
import os
import tempfile
import unittest

import grade_navigation as nav

# A doc where "## Retry policy" (the gold heading) sits at line 6.
DOC = (
    "# Config\n\n"
    "## Filler\n"
    "noise\n\n"
    "## Retry policy\n\n"
    "The current retry policy allows up to 5 attempts before giving up.\n"
)

TASK_KEY = {
    "id": "T1",
    "gold_spans": [{"file": "knowledge/small.md", "heading": "Retry policy"}],
    "correct_signature": "5 attempts",
    "decoys": [{"id": "D1", "signature": "3 attempts"}],
}


def transcript(*records):
    return "\n".join(json.dumps(record) for record in records) + "\n"


def result_record(text):
    return {
        "type": "result",
        "result": text,
        "usage": {
            "input_tokens": 100,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 10,
        },
        "total_cost_usd": 0.01,
    }


def read_block(file_path, **params):
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": file_path, **params},
                }
            ]
        },
    }


def bash_block(command):
    return {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": command}}
            ]
        },
    }


class GradeNavigationTest(unittest.TestCase):
    def setUp(self):
        self.tree = tempfile.mkdtemp()
        docs_dir = os.path.join(self.tree, "knowledge")
        os.makedirs(docs_dir)
        with open(os.path.join(docs_dir, "small.md"), "w", encoding="utf-8") as handle:
            handle.write(DOC)

    def _transcript_file(self, text):
        path = os.path.join(self.tree, "run.log")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_full_read_of_gold_scores_success_and_recall_one(self):
        path = self._transcript_file(
            transcript(
                read_block("knowledge/small.md"),  # full read — no offset/limit
                result_record(
                    "The current policy allows 5 attempts.\nANSWER: 5 attempts"
                ),
            )
        )
        result = nav.grade_transcript(path, TASK_KEY, self.tree)
        self.assertTrue(result["success"])
        self.assertFalse(result["decoy_hit"])
        self.assertEqual(result["context_recall"], 1.0)
        self.assertTrue(result["protocol_ok"])
        self.assertEqual(result["context_tokens"], 100)

    def test_decoy_answer_scores_failure_and_decoy_hit_and_zero_recall(self):
        path = self._transcript_file(
            transcript(
                read_block(
                    "knowledge/small.md", offset=1, limit=5
                ),  # only the top — not the gold section
                result_record("Looks like 3 attempts.\nANSWER: 3 attempts"),
            )
        )
        result = nav.grade_transcript(path, TASK_KEY, self.tree)
        self.assertFalse(result["success"])
        self.assertTrue(result["decoy_hit"])
        self.assertEqual(result["context_recall"], 0.0)

    def test_missing_answer_line_is_protocol_fail(self):
        path = self._transcript_file(transcript(result_record("I could not find it.")))
        result = nav.grade_transcript(path, TASK_KEY, self.tree)
        self.assertFalse(result["protocol_ok"])
        self.assertFalse(result["success"])

    def test_terse_numeric_answer_matches_but_substring_does_not(self):
        # Regression: the first live pilot answered "5", not "5 attempts" — a bare
        # value must match word-boundary, while "15" must not match "5".
        key = {
            "id": "T1",
            "gold_spans": [{"file": "knowledge/small.md", "heading": "Retry policy"}],
            "correct_signature": "5",
            "decoys": [{"id": "D1", "signature": "3"}],
        }
        terse = self._transcript_file(
            transcript(
                read_block("knowledge/small.md"), result_record("It allows 5.\nANSWER: 5")
            )
        )
        self.assertTrue(nav.grade_transcript(terse, key, self.tree)["success"])
        wrong = self._transcript_file(
            transcript(
                read_block("knowledge/small.md"), result_record("Maybe 15.\nANSWER: 15")
            )
        )
        self.assertFalse(nav.grade_transcript(wrong, key, self.tree)["success"])

    def test_knowledge_py_section_of_gold_counts_for_recall(self):
        path = self._transcript_file(
            transcript(
                bash_block(
                    'python3 scripts/knowledge.py section knowledge/small.md "Retry policy"'
                ),
                result_record("ANSWER: 5 attempts"),
            )
        )
        result = nav.grade_transcript(path, TASK_KEY, self.tree)
        self.assertEqual(result["context_recall"], 1.0)
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
