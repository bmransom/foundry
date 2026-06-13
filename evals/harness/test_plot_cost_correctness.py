#!/usr/bin/env python3
"""Unit tests for plot_cost_correctness. Stdlib unittest; no API."""

import unittest

import plot_cost_correctness as plot


def summary(arm, tokens, success, fixture="navigation"):
    return {
        "event": "summary",
        "fixture": fixture,
        "arm": arm,
        "mean_context_tokens": tokens,
        "mean_success": success,
    }


class CollectPointsTest(unittest.TestCase):
    def test_collects_arm_points_with_cost_and_correctness(self):
        points, missing = plot.collect_points(
            [summary("full-load", 5000, 1.0), summary("disclosure", 1200, 1.0)]
        )
        self.assertEqual(len(points), 2)
        self.assertEqual(missing, [])
        by_arm = {p["arm"]: p for p in points}
        self.assertEqual(by_arm["disclosure"]["x"], 1200.0)
        self.assertEqual(by_arm["full-load"]["y"], 1.0)

    def test_summary_without_cost_is_missing_not_fabricated(self):
        points, missing = plot.collect_points(
            [
                {
                    "event": "summary",
                    "fixture": "reviewer",
                    "arm": "reviewer",
                    "mean_recall": 0.9,
                }
            ]
        )
        self.assertEqual(points, [])
        self.assertEqual(missing, [("reviewer", "reviewer")])

    def test_fixture_scope_summary_is_ignored(self):
        points, missing = plot.collect_points(
            [
                {
                    "event": "summary",
                    "fixture": "navigation",
                    "scope": "fixture",
                    "discriminating": True,
                }
            ]
        )
        self.assertEqual(points, [])
        self.assertEqual(missing, [])

    def test_falls_back_to_mean_recall_when_no_success_field(self):
        points, _ = plot.collect_points(
            [
                {
                    "event": "summary",
                    "fixture": "reviewer",
                    "arm": "reviewer",
                    "mean_context_tokens": 3000,
                    "mean_recall": 0.8,
                }
            ]
        )
        self.assertEqual(points[0]["y"], 0.8)
        self.assertEqual(points[0]["y_field"], "mean_recall")


class FrontierTest(unittest.TestCase):
    def test_dominated_point_excluded(self):
        cheap = {"fixture": "f", "arm": "A", "x": 1000, "y": 1.0}
        pricey_equal = {"fixture": "f", "arm": "B", "x": 5000, "y": 1.0}
        frontier = plot.pareto_frontier([cheap, pricey_equal])
        self.assertEqual([p["arm"] for p in frontier], ["A"])

    def test_genuine_tradeoff_keeps_both(self):
        cheap_rough = {"fixture": "f", "arm": "A", "x": 1000, "y": 0.6}
        pricey_accurate = {"fixture": "f", "arm": "B", "x": 4000, "y": 0.95}
        frontier = plot.pareto_frontier([cheap_rough, pricey_accurate])
        self.assertEqual(sorted(p["arm"] for p in frontier), ["A", "B"])


class RenderTest(unittest.TestCase):
    def test_svg_has_points_and_a_frontier(self):
        # A genuine tradeoff so two points stay on the frontier and a polyline is drawn.
        points, missing = plot.collect_points(
            [summary("full-load", 5000, 1.0), summary("disclosure", 1200, 0.7)]
        )
        svg = plot.render_svg(points, missing, "Nav")
        self.assertIn("<svg", svg)
        self.assertIn("full-load", svg)
        self.assertIn("disclosure", svg)
        self.assertIn("polyline", svg)

    def test_missing_cost_is_noted_in_svg(self):
        svg = plot.render_svg(
            [
                {
                    "fixture": "f",
                    "arm": "A",
                    "x": 1000,
                    "y": 1.0,
                    "y_field": "mean_success",
                }
            ],
            [("reviewer", "reviewer")],
            "T",
        )
        self.assertIn("no context cost recorded", svg)


if __name__ == "__main__":
    unittest.main()
