#!/usr/bin/env python3
"""Unit tests for plot_sweep. Stdlib unittest; no API."""

import unittest

import plot_sweep as sweep


def summ(arm, size, tokens, success=1.0):
    return {
        "event": "summary",
        "fixture": "navigation-breadth",
        "arm": arm,
        "corpus_size": size,
        "mean_loaded_content_tokens": tokens,
        "mean_success": success,
    }


class CollectTest(unittest.TestCase):
    def test_groups_by_arm_sorted_by_corpus_size(self):
        series = sweep.collect(
            [
                summ("native", 100, 5000),
                summ("native", 5, 200),
                summ("hybrid", 100, 300),
            ]
        )
        self.assertEqual([x for x, _, _ in series["native"]], [5, 100])
        self.assertEqual(len(series["hybrid"]), 1)

    def test_ignores_untagged_and_fixture_scope(self):
        series = sweep.collect(
            [
                {
                    "event": "summary",
                    "arm": "x",
                    "mean_loaded_content_tokens": 1,
                },  # no corpus_size
                {"event": "summary", "scope": "fixture", "corpus_size": 5},
            ]
        )
        self.assertEqual(dict(series), {})


class RenderTest(unittest.TestCase):
    def test_svg_has_arms_and_polylines(self):
        series = sweep.collect(
            [
                summ("native", 5, 200),
                summ("native", 100, 5000),
                summ("hybrid", 5, 300),
                summ("hybrid", 100, 350),
            ]
        )
        svg = sweep.render_svg(series, "T")
        self.assertIn("<svg", svg)
        self.assertIn("native", svg)
        self.assertIn("hybrid", svg)
        self.assertIn("polyline", svg)


if __name__ == "__main__":
    unittest.main()
