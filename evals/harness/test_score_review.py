"""Unit tests for score_review.py — the reviewer-eval scorer must itself discriminate.

Each test writes a canned answer key plus one or more canned findings texts to
a tmp dir and runs score_review.py as a subprocess (the real CLI: argv, stdout
NDJSON, exit code).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCORE_REVIEW = Path(__file__).resolve().parent / "score_review.py"

ANSWER_KEY = {
    "fixture": "reviewer",
    "violations": [
        {"id": "V1", "signature": "basket", "type": "debt-term"},
        {"id": "V2", "signature": "row item", "type": "debt-term"},
        {"id": "V3", "signature": "PriceLattice", "type": "uncited-coined-term"},
        {"id": "V4", "signature": "very basically", "type": "needless-qualifier"},
        {"id": "V5", "signature": "rounding_residue", "type": "prose-should-be-table"},
    ],
    "decoys": [
        {"id": "D1", "signature": "Snapshot", "type": "coined-term-with-prior-art"},
        {"id": "D2", "signature": "estimate", "type": "debt-term-in-replaces-context"},
    ],
}

# Full-recall findings under the FLAGGED-footer protocol: all 5 violation
# signatures appear in FLAGGED lines; decoy signatures appear only in
# praise-of-clean-content prose above the footer.
FULL_RECALL_FINDINGS = """\
## roadmap/specs/widget-pricing/design.md

- L17: "basket" is glossary debt; use Order.
- L28: "row item" is glossary debt; use Line.
- L36: PriceLattice is coined with no prior art; cite one or record why none fits.
- L20: "very basically" — needless qualifier; delete it.
- L50: the field run ending in rounding_residue should be a table.

Clean files: AGENTS.md, knowledge/glossary.md.
Note: Snapshot is a coined term with recorded prior art (clean).
Note: estimate is used correctly in the replaces context (clean).
Highest-priority fix: replace the debt terms with glossary vocabulary.

FLAGGED: basket
FLAGGED: row item
FLAGGED: PriceLattice
FLAGGED: very basically
FLAGGED: rounding_residue
"""


def run_scorer(findings_texts, answer_key=ANSWER_KEY, extra_args=None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        key_path = tmp_path / "answer-key.json"
        key_path.write_text(json.dumps(answer_key))
        findings_paths = []
        for index, text in enumerate(findings_texts, start=1):
            findings_path = tmp_path / f"run{index}.findings.txt"
            findings_path.write_text(text)
            findings_paths.append(str(findings_path))
        completed = subprocess.run(
            [sys.executable, str(SCORE_REVIEW), str(key_path)]
            + findings_paths
            + (extra_args or []),
            capture_output=True,
            text=True,
        )
    records = [json.loads(line) for line in completed.stdout.splitlines() if line]
    return completed, records


def case_records(records):
    return [r for r in records if r["event"] == "eval_case"]


def summary_of(records):
    summaries = [r for r in records if r["event"] == "summary"]
    assert len(summaries) == 1, f"expected one summary record, got {summaries}"
    return summaries[0]


def verdict_of(records, run, case):
    matches = [
        r for r in case_records(records) if r["run"] == run and r["case"] == case
    ]
    assert matches, (
        f"no record for run {run} case {case!r}; "
        f"cases: {[(r['run'], r['case']) for r in case_records(records)]}"
    )
    return matches[0]["verdict"]


class FullRecallTest(unittest.TestCase):
    def test_all_detected_no_decoys_passes(self):
        completed, records = run_scorer([FULL_RECALL_FINDINGS])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        summary = summary_of(records)
        self.assertEqual(summary["verdict"], "pass")
        self.assertEqual(summary["mean_recall"], 1.0)
        self.assertEqual(summary["min_recall"], 1.0)
        self.assertEqual(summary["per_run_recall"], [1.0])
        self.assertEqual(summary["decoy_hits"], 0)
        self.assertEqual(summary["runs"], 1)

    def test_one_eval_case_per_violation_and_decoy(self):
        _, records = run_scorer([FULL_RECALL_FINDINGS])
        cases = sorted(r["case"] for r in case_records(records))
        self.assertEqual(
            cases,
            sorted(
                [f"violation:{v['id']}" for v in ANSWER_KEY["violations"]]
                + [f"decoy:{d['id']}" for d in ANSWER_KEY["decoys"]]
            ),
        )
        for record in case_records(records):
            self.assertEqual(record["fixture"], "reviewer")
            self.assertEqual(record["verdict"], "pass")
            self.assertEqual(
                sorted(record), ["case", "detail", "event", "fixture", "run", "verdict"]
            )

    def test_detection_is_case_insensitive(self):
        # FLAGGED lines with uppercase violation signatures — should still detect
        shouting = """\
## roadmap/specs/widget-pricing/design.md

- BASKET is glossary debt.

FLAGGED: BASKET
FLAGGED: ROW ITEM
FLAGGED: PRICELATTICE
FLAGGED: VERY BASICALLY
FLAGGED: ROUNDING_RESIDUE
"""
        completed, records = run_scorer([shouting])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(summary_of(records)["mean_recall"], 1.0)


class RecallBarTest(unittest.TestCase):
    def test_missed_violations_below_bar_fail(self):
        three_of_five = """\
Review findings.

FLAGGED: basket
FLAGGED: row item
FLAGGED: PriceLattice
"""
        completed, records = run_scorer([three_of_five])
        self.assertNotEqual(completed.returncode, 0)
        summary = summary_of(records)
        self.assertEqual(summary["verdict"], "fail")
        self.assertEqual(summary["mean_recall"], 0.6)
        self.assertEqual(verdict_of(records, 1, "violation:V4"), "fail")
        self.assertEqual(verdict_of(records, 1, "violation:V5"), "fail")

    def test_recall_exactly_at_bar_passes(self):
        four_of_five = """\
Review findings.

FLAGGED: basket
FLAGGED: row item
FLAGGED: PriceLattice
FLAGGED: very basically
"""
        completed, records = run_scorer([four_of_five])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        summary = summary_of(records)
        self.assertEqual(summary["verdict"], "pass")
        self.assertEqual(summary["mean_recall"], 0.8)

    def test_empty_findings_score_zero_recall(self):
        completed, records = run_scorer([""])
        self.assertNotEqual(completed.returncode, 0)
        summary = summary_of(records)
        self.assertEqual(summary["mean_recall"], 0.0)
        self.assertEqual(summary["verdict"], "fail")


class DecoyTest(unittest.TestCase):
    def test_decoy_hit_fails_despite_full_recall(self):
        # Decoy signature appears inside a FLAGGED line — should register as a hit
        findings_with_flagged_decoy = FULL_RECALL_FINDINGS + "FLAGGED: Snapshot\n"
        completed, records = run_scorer([findings_with_flagged_decoy])
        self.assertNotEqual(completed.returncode, 0)
        summary = summary_of(records)
        self.assertEqual(summary["verdict"], "fail")
        self.assertEqual(summary["mean_recall"], 1.0)
        self.assertEqual(summary["decoy_hits"], 1)
        self.assertEqual(verdict_of(records, 1, "decoy:D1"), "fail")
        self.assertEqual(verdict_of(records, 1, "decoy:D2"), "pass")

    def test_decoy_in_praise_prose_not_in_flagged_is_not_a_hit(self):
        # Agent correctly praises Snapshot and estimate as clean — mentions them
        # in prose but NOT in FLAGGED lines — should yield recall 1.0, decoys 0
        findings = """\
## roadmap/specs/widget-pricing/design.md

- L17: "basket" is glossary debt; use Order.
- L28: "row item" is glossary debt; use Line.
- L36: PriceLattice is coined with no prior art; cite one.
- L20: "very basically" — needless qualifier.
- L50: rounding_residue should be a table.

Note: Snapshot is a coined term with recorded prior art — no flag needed.
Note: estimate is used correctly in the replaces context — no flag needed.

FLAGGED: basket
FLAGGED: row item
FLAGGED: PriceLattice
FLAGGED: very basically
FLAGGED: rounding_residue
"""
        completed, records = run_scorer([findings])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        summary = summary_of(records)
        self.assertEqual(summary["mean_recall"], 1.0)
        self.assertEqual(summary["decoy_hits"], 0)
        self.assertEqual(verdict_of(records, 1, "decoy:D1"), "pass")
        self.assertEqual(verdict_of(records, 1, "decoy:D2"), "pass")

    def test_decoy_inside_flagged_line_registers_as_hit(self):
        # Explicit test: a decoy signature appearing in a FLAGGED: line is a hit
        findings = """\
Findings.

FLAGGED: basket
FLAGGED: row item
FLAGGED: PriceLattice
FLAGGED: very basically
FLAGGED: rounding_residue
FLAGGED: Snapshot
"""
        completed, records = run_scorer([findings])
        self.assertNotEqual(completed.returncode, 0)
        summary = summary_of(records)
        self.assertEqual(summary["decoy_hits"], 1)
        self.assertEqual(verdict_of(records, 1, "decoy:D1"), "fail")

    def test_missing_flagged_block_is_protocol_fail(self):
        # No FLAGGED: lines at all — scorer must emit a protocol eval_case fail
        # and score the run recall 0
        findings = """\
## roadmap/specs/widget-pricing/design.md

- basket is glossary debt.
- row item is glossary debt.
- PriceLattice is coined.
- very basically is needless.
- rounding_residue should be a table.
"""
        completed, records = run_scorer([findings])
        self.assertNotEqual(completed.returncode, 0)
        summary = summary_of(records)
        self.assertEqual(summary["verdict"], "fail")
        self.assertEqual(summary["mean_recall"], 0.0)
        # A protocol eval_case record must be emitted for the run
        protocol_cases = [
            r
            for r in case_records(records)
            if r["case"] == "protocol" and r["verdict"] == "fail"
        ]
        self.assertEqual(
            len(protocol_cases),
            1,
            f"expected one protocol fail, got {case_records(records)}",
        )


class MultiRunTest(unittest.TestCase):
    def test_mean_and_min_recall_across_runs(self):
        three_of_five = """\
Findings.

FLAGGED: basket
FLAGGED: row item
FLAGGED: PriceLattice
"""
        completed, records = run_scorer([FULL_RECALL_FINDINGS, three_of_five])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        summary = summary_of(records)
        self.assertEqual(summary["runs"], 2)
        self.assertEqual(summary["per_run_recall"], [1.0, 0.6])
        self.assertEqual(summary["mean_recall"], 0.8)
        self.assertEqual(summary["min_recall"], 0.6)
        self.assertEqual(summary["verdict"], "pass")
        self.assertEqual(verdict_of(records, 1, "violation:V4"), "pass")
        self.assertEqual(verdict_of(records, 2, "violation:V4"), "fail")

    def test_decoy_hits_sum_across_runs(self):
        with_decoy = FULL_RECALL_FINDINGS + "FLAGGED: Snapshot\nFLAGGED: estimate\n"
        completed, records = run_scorer([with_decoy, with_decoy])
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(summary_of(records)["decoy_hits"], 4)


class ResultsFileTest(unittest.TestCase):
    def test_results_flag_appends_the_same_ndjson(self):
        with tempfile.TemporaryDirectory() as tmp:
            results_path = Path(tmp) / "results.ndjson"
            key_path = Path(tmp) / "answer-key.json"
            key_path.write_text(json.dumps(ANSWER_KEY))
            findings_path = Path(tmp) / "run1.findings.txt"
            findings_path.write_text(FULL_RECALL_FINDINGS)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCORE_REVIEW),
                    str(key_path),
                    str(findings_path),
                    "--results",
                    str(results_path),
                ],
                capture_output=True,
                text=True,
            )
            stdout_records = [
                json.loads(line) for line in completed.stdout.splitlines() if line
            ]
            file_records = [
                json.loads(line)
                for line in results_path.read_text().splitlines()
                if line
            ]
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(stdout_records, file_records)


class BadInputTest(unittest.TestCase):
    def test_missing_findings_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            key_path = Path(tmp) / "answer-key.json"
            key_path.write_text(json.dumps(ANSWER_KEY))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCORE_REVIEW),
                    str(key_path),
                    os.path.join(tmp, "absent.txt"),
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)

    def test_answer_key_without_violations_exits_2(self):
        completed, _ = run_scorer(
            ["anything"],
            answer_key={"fixture": "reviewer", "violations": [], "decoys": []},
        )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
