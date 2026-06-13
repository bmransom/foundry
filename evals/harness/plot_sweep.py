#!/usr/bin/env python3
"""Plot navigation cost vs corpus size from a breadth-eval NDJSON: one line per
arm, x = corpus size, y = content tokens loaded. Shows the crossover where
structure-aware navigation overtakes grep as the corpus grows. Hand-rolled SVG,
stdlib only; consumes NDJSON, shares no grader code (AC-2.4).

Usage: plot_sweep.py <breadth.ndjson> -o out.svg [--title T]
"""

import argparse
import json
import sys
from collections import defaultdict

PALETTE = ("#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2")


def collect(records):
    """series[arm] = sorted [(corpus_size, loaded_tokens, mean_success)] from the
    per-arm summary records tagged with corpus_size."""
    series = defaultdict(list)
    for record in records:
        if record.get("event") != "summary" or record.get("scope") == "fixture":
            continue
        if "corpus_size" not in record or "mean_loaded_content_tokens" not in record:
            continue
        series[record["arm"]].append(
            (
                int(record["corpus_size"]),
                float(record["mean_loaded_content_tokens"]),
                float(record.get("mean_success", 0.0)),
            )
        )
    for arm in series:
        series[arm].sort()
    return series


def render_svg(series, title):
    width, height = 760, 500
    left, right, top, bottom = 90, 150, 60, 70
    plot_w, plot_h = width - left - right, height - top - bottom
    xs = [x for points in series.values() for x, _, _ in points] or [1]
    ys = [y for points in series.values() for _, y, _ in points] or [1]
    max_x = max(xs) * 1.1 or 1
    max_y = max(ys) * 1.1 or 1

    def px(value):
        return left + (value / max_x) * plot_w

    def py(value):
        return top + (1 - value / max_y) * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'font-family="ui-sans-serif, system-ui, sans-serif" font-size="13">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="16" font-weight="600">{title}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#111"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#111"/>',
        f'<text x="{left + plot_w / 2}" y="{height - 24}" text-anchor="middle">corpus size (docs) →</text>',
        f'<text x="24" y="{top + plot_h / 2}" text-anchor="middle" '
        f'transform="rotate(-90 24 {top + plot_h / 2})">content tokens loaded — lower is better →</text>',
    ]
    for frac in (0.0, 0.5, 1.0):
        out.append(
            f'<text x="{left + frac * plot_w}" y="{top + plot_h + 20}" text-anchor="middle" fill="#555">{int(max_x * frac)}</text>'
        )
        out.append(
            f'<text x="{left - 8}" y="{py(max_y * frac) + 4}" text-anchor="end" fill="#555">{int(max_y * frac)}</text>'
        )
    for index, (arm, points) in enumerate(sorted(series.items())):
        color = PALETTE[index % len(PALETTE)]
        line = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y, _ in points)
        out.append(
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2"/>'
        )
        for x, y, _ in points:
            out.append(
                f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="4" fill="{color}"/>'
            )
        legend_y = top + 10 + index * 20
        out.append(
            f'<line x1="{left + plot_w + 12}" y1="{legend_y}" x2="{left + plot_w + 30}" y2="{legend_y}" stroke="{color}" stroke-width="2"/>'
        )
        out.append(f'<text x="{left + plot_w + 34}" y="{legend_y + 4}">{arm}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--title", default="Navigation cost vs corpus size")
    args = parser.parse_args()
    records = []
    with open(args.results, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    series = collect(records)
    if not series:
        print(
            "plot_sweep: no corpus_size-tagged summary records found", file=sys.stderr
        )
        sys.exit(1)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(render_svg(series, args.title) + "\n")
    print(f"plot_sweep: {len(series)} arms -> {args.output}")


if __name__ == "__main__":
    main()
