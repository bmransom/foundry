#!/usr/bin/env python3
"""Plot correctness vs context cost for one or more eval result files.

Reads eval NDJSON (the `summary` records), plots each arm as a point — context
tokens on x, correctness on y — and marks the Pareto frontier (highest
correctness at lowest cost). Emits a hand-rolled SVG: zero dependencies, embeds
in the vitepress site and renders on GitHub. Shares no code with any grader; it
consumes results only (AC-2.4).

Correctness is read from the first present of these summary fields (so the same
plotter serves every eval): mean_success, then mean_recall. Cost is
mean_context_tokens; a summary without it is reported as missing, never
fabricated (AC-3.2).

Usage:
  plot_cost_correctness.py <results.ndjson> [<more.ndjson> ...] -o out.svg [--title T]
"""

import argparse
import json
import sys

CORRECTNESS_FIELDS = ("mean_success", "mean_recall")
PALETTE = ("#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2")


def collect_points(records):
    """Return (points, missing) from summary records. A point is
    {fixture, arm, x (context tokens), y (correctness), y_field}. `missing` lists
    (fixture, arm) summaries that carry correctness but no context cost."""
    points = []
    missing = []
    for record in records:
        if record.get("event") != "summary" or record.get("scope") == "fixture":
            continue
        y_field = next((f for f in CORRECTNESS_FIELDS if f in record), None)
        if y_field is None:
            continue
        fixture = record.get("fixture", "eval")
        arm = record.get("arm", fixture)
        cost = record.get("mean_loaded_content_tokens") or record.get(
            "mean_context_tokens"
        )
        if not cost:
            missing.append((fixture, arm))
            continue
        points.append(
            {
                "fixture": fixture,
                "arm": arm,
                "x": float(cost),
                "y": float(record[y_field]),
                "y_field": y_field,
            }
        )
    return points, missing


def pareto_frontier(points):
    """Points not dominated by any other — lower cost is better, higher
    correctness is better. Returned sorted by x for drawing."""
    frontier = []
    for candidate in points:
        dominated = any(
            other is not candidate
            and other["x"] <= candidate["x"]
            and other["y"] >= candidate["y"]
            and (other["x"] < candidate["x"] or other["y"] > candidate["y"])
            for other in points
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda p: p["x"])


def _esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(points, missing, title):
    width, height = 760, 500
    left, right, top, bottom = 90, 40, 60, 70
    plot_w, plot_h = width - left - right, height - top - bottom
    max_x = max((p["x"] for p in points), default=1.0) * 1.1 or 1.0

    def px(x):
        return left + (x / max_x) * plot_w

    def py(y):  # correctness 0..1, inverted for SVG
        return top + (1 - y) * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'font-family="ui-sans-serif, system-ui, sans-serif" font-size="13">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="16" font-weight="600">{_esc(title)}</text>',
        # axes
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#111"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#111"/>',
        f'<text x="{left + plot_w / 2}" y="{height - 24}" text-anchor="middle">context cost (tokens) — lower is better →</text>',
        f'<text x="24" y="{top + plot_h / 2}" text-anchor="middle" transform="rotate(-90 24 {top + plot_h / 2})">correctness — higher is better →</text>',
    ]
    # y gridlines/ticks at 0,.25,.5,.75,1
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = py(tick)
        out.append(
            f'<line x1="{left}" y1="{y}" x2="{left + plot_w}" y2="{y}" stroke="#eee"/>'
        )
        out.append(
            f'<text x="{left - 8}" y="{y + 4}" text-anchor="end" fill="#555">{tick:.2f}</text>'
        )
    # x ticks at 0, mid, max
    for frac in (0.0, 0.5, 1.0):
        x = left + frac * plot_w
        out.append(
            f'<text x="{x}" y="{top + plot_h + 20}" text-anchor="middle" fill="#555">{int(max_x * frac)}</text>'
        )
    # Pareto frontier
    frontier = pareto_frontier(points)
    if len(frontier) >= 2:
        pts = " ".join(f"{px(p['x']):.1f},{py(p['y']):.1f}" for p in frontier)
        out.append(
            f'<polyline points="{pts}" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="5 4"/>'
        )
    # points, coloured by fixture
    fixtures = sorted({p["fixture"] for p in points})
    color = {fx: PALETTE[i % len(PALETTE)] for i, fx in enumerate(fixtures)}
    on_frontier = {id(p) for p in frontier}
    for p in points:
        cx, cy = px(p["x"]), py(p["y"])
        out.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{color[p["fixture"]]}" '
            f'stroke="#111" stroke-width="{2 if id(p) in on_frontier else 0}"/>'
        )
        out.append(f'<text x="{cx + 10:.1f}" y="{cy + 4:.1f}">{_esc(p["arm"])}</text>')
    # legend (when >1 fixture)
    if len(fixtures) > 1:
        for i, fx in enumerate(fixtures):
            ly = top + 6 + i * 18
            out.append(
                f'<rect x="{left + plot_w - 150}" y="{ly - 10}" width="12" height="12" fill="{color[fx]}"/>'
            )
            out.append(f'<text x="{left + plot_w - 134}" y="{ly}">{_esc(fx)}</text>')
    if missing:
        note = "no context cost recorded: " + ", ".join(
            f"{fx}/{arm}" for fx, arm in missing
        )
        out.append(
            f'<text x="{left}" y="{height - 6}" fill="#dc2626" font-size="11">{_esc(note)}</text>'
        )
    out.append("</svg>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", help="eval NDJSON result file(s)")
    parser.add_argument("-o", "--output", required=True, help="SVG output path")
    parser.add_argument("--title", default="Correctness vs context cost")
    args = parser.parse_args()

    records = []
    for path in args.results:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    points, missing = collect_points(records)
    if not points and not missing:
        print(
            "plot_cost_correctness: no summary records with correctness found",
            file=sys.stderr,
        )
        sys.exit(1)
    svg = render_svg(points, missing, args.title)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(svg + "\n")
    print(
        f"plot_cost_correctness: {len(points)} point(s) -> {args.output}"
        + (f" ({len(missing)} missing cost)" if missing else "")
    )


if __name__ == "__main__":
    main()
