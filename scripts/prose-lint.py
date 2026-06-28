#!/usr/bin/env python3
# foundry-template: prose-lint v1
"""Lint context-resident prose for banned filler phrases — a deterministic writing-style gate.

Usage: prose-lint.py <file.md> [file.md ...]

Fails (exit 1) on any banned filler phrase: a multi-word hedge disciplined prose omits
(review-convergence US-3). The phrases are generic English — no repo vocabulary, so the
verbatim twin ships no repo-specific content (mechanisms-not-content).

Out of scope, by design: subjective taste (passive voice, a paragraph better as a table) and
context-scoped glossary debt terms (e.g. "issue" only for board rows) are *judge* calls, not
deterministic lints. Pure stdlib; mirrors check-board / knowledge.
"""

import re
import sys

# Multi-word, objectively removable filler. Case-insensitive. Generic English only.
BANNED = [
    "very basically",
    "basically just",
    "needless to say",
    "it goes without saying",
    "for all intents and purposes",
    "as a matter of fact",
    "at the end of the day",
    "it could perhaps be considered",
]
PATTERNS = [(p, re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)) for p in BANNED]


def lint_text(lines):
    """Yield (lineno, phrase) for each banned phrase, skipping fenced code blocks."""
    in_fence = False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for phrase, rx in PATTERNS:
            if rx.search(line):
                yield i, phrase


def check(paths):
    violations = 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().split("\n")
        except OSError as err:
            print(f"prose-lint: cannot read {path}: {err}", file=sys.stderr)
            return 2
        for lineno, phrase in lint_text(lines):
            print(f"prose-lint: {path}:{lineno}: banned filler phrase {phrase!r}")
            violations += 1
    if violations:
        print(f"prose-lint: FAIL ({violations} issue(s))")
        return 1
    print(f"prose-lint: OK ({len(paths)} file(s))")
    return 0


def main(argv):
    if len(argv) < 2:
        print("usage: prose-lint.py <file.md> [file.md ...]", file=sys.stderr)
        return 2
    return check(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
