#!/usr/bin/env python3
"""Materialize the navigation fixture tree deterministically.

Builds evals/fixtures/navigation/tree/ with three docs (small/medium/large) at
roughly 100 / 500 / 2000 lines. Each holds one gold section (the answer) and,
immediately before it, a near-duplicate decoy section with a different value — so
a naive grep returns both and the arm must disambiguate. Gold/decoy strings match
answer-key.json. Filler sections are deterministic noise giving the large doc
genuine length. Also drops scripts/docs.py into the tree so the disclosure arm
can run it.

The tree is generated (gitignored), not committed: the committed ground truth is
this script plus answer-key.json / tasks.json.

Run: python3 evals/fixtures/navigation/build_tree.py
"""

import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TREE = os.path.join(HERE, "tree")

# name, target_lines, title, decoy_heading, decoy_body, gold_heading, gold_body
DOCS = [
    (
        "small.md",
        100,
        "Service configuration reference",
        "Legacy retry",
        "The legacy retry path allowed only 3 attempts and has been removed.",
        "Retry policy",
        "The current retry policy allows up to **5 attempts** before giving up.",
    ),
    (
        "medium.md",
        500,
        "Public API reference",
        "Burst limit",
        "A short burst may briefly exceed the sustained rate, up to 100 requests in ten seconds.",
        "Sustained rate limit",
        "The public API sustains **1000 requests** per minute per API key.",
    ),
    (
        "large.md",
        2000,
        "Gateway operations handbook",
        "Staging gateway profile",
        "The staging gateway profile sets the connection idle timeout to 30 seconds.",
        "Production gateway profile",
        "The production gateway profile sets the connection idle timeout to 90 seconds.",
    ),
]

FILLER_BODY = (
    "This section documents an unrelated configuration knob. It has no bearing on\n"
    "the value under test and exists only to give the document realistic length so\n"
    "full-load and selective navigation differ in context cost."
)


def filler_section(index):
    return f"## Filler topic {index}\n\n{FILLER_BODY}\n\n"


def line_count(text):
    return text.count("\n")


def build_doc(target_lines, title, decoy_heading, decoy_body, gold_heading, gold_body):
    head = f"# {title}\n\n"
    decoy_and_gold = (
        f"## {decoy_heading}\n\n{decoy_body}\n\n## {gold_heading}\n\n{gold_body}\n\n"
    )
    body = ""
    index = 0
    while line_count(head + body + decoy_and_gold) < target_lines:
        index += 1
        body += filler_section(index)
    return head + body + decoy_and_gold


def main():
    docs_dir = os.path.join(TREE, "knowledge")
    os.makedirs(docs_dir, exist_ok=True)
    sizes = {}
    for name, target, title, decoy_heading, decoy_body, gold_heading, gold_body in DOCS:
        text = build_doc(
            target, title, decoy_heading, decoy_body, gold_heading, gold_body
        )
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as handle:
            handle.write(text)
        sizes[name] = line_count(text)
    scripts_dir = os.path.join(TREE, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    shutil.copyfile(
        os.path.join(REPO, "scripts", "docs.py"), os.path.join(scripts_dir, "docs.py")
    )
    print(f"navigation fixture: built {sizes} + scripts/docs.py in {TREE}")


if __name__ == "__main__":
    main()
