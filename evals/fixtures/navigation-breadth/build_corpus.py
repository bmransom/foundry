#!/usr/bin/env python3
"""Materialize the breadth navigation fixture: a corpus of N docs where the
answer lives in ONE doc (gateway.md), with decoys (staging.md, edge.md) and
filler hiding it. Tests discovery ("which doc?") and how navigation cost scales
with corpus size.

The answer-key always points to gateway.md, independent of N. Every filler doc
mentions "timeout" in a benign context, so a naive `grep -r timeout` returns ~N
hits — the noise that grows with the corpus and that a catalog/structure-aware
approach should avoid.

Run: python3 evals/fixtures/navigation-breadth/build_corpus.py --count 50
"""

import argparse
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def frontmatter(title, description, kind="reference"):
    return f"---\ntitle: {title}\ndescription: {description}\nkind: {kind}\n---\n\n"


GOLD_NAME = "gateway.md"
GOLD_DOC = (
    frontmatter(
        "Gateway profiles",
        "Production and staging gateway connection profiles and idle timeouts.",
    )
    + "# Gateway profiles\n\n## Overview\n\nGateway connection profiles per environment.\n\n"
    + "## Production gateway profile\n\nThe production gateway profile sets the connection idle timeout to 90 seconds.\n"
)

DECOY_DOCS = {
    "staging.md": (
        frontmatter(
            "Staging gateway", "Staging environment gateway settings and timeouts."
        )
        + "# Staging gateway\n\n## Staging gateway profile\n\nThe staging gateway profile sets the connection idle timeout to 30 seconds.\n"
    ),
    "edge.md": (
        frontmatter("Edge proxy", "Edge proxy and gateway timeouts.")
        + "# Edge proxy\n\n## Edge gateway profile\n\nThe edge gateway profile sets the connection idle timeout to 45 seconds.\n"
    ),
}

DOCS_CONFIG = (
    '{\n  "kinds": ["reference", "architecture", "guide", "decision"],\n'
    '  "required_fields": ["title", "description", "kind"],\n'
    '  "doc_globs": ["knowledge/*.md"],\n'
    '  "exclude_substrings": ["/node_modules/", "/.vitepress/"]\n}\n'
)


def filler_doc(index):
    return (
        frontmatter(
            f"Service {index:03d} notes", f"Operational notes for service {index:03d}."
        )
        + f"# Service {index:03d} notes\n\n## Overview\n\nRoutine configuration for service {index:03d}.\n\n"
        + f"## Connection settings\n\nThis service uses a request timeout of {200 + index % 50} ms "
        + "and a connection profile tuned for its workload.\n\n"
        + f"## Notes\n\nNothing unusual to report for service {index:03d}.\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count", type=int, default=50, help="total docs in the corpus (>= 3)"
    )
    parser.add_argument("--out", default=os.path.join(HERE, "tree"))
    args = parser.parse_args()
    count = max(args.count, 3)

    docs_dir = os.path.join(args.out, "knowledge")
    if os.path.isdir(docs_dir):
        shutil.rmtree(docs_dir)  # rebuild so the corpus size is exact
    os.makedirs(docs_dir)

    with open(os.path.join(docs_dir, GOLD_NAME), "w", encoding="utf-8") as handle:
        handle.write(GOLD_DOC)
    for name, text in DECOY_DOCS.items():
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as handle:
            handle.write(text)
    for index in range(count - 1 - len(DECOY_DOCS)):
        with open(
            os.path.join(docs_dir, f"topic_{index:03d}.md"), "w", encoding="utf-8"
        ) as handle:
            handle.write(filler_doc(index))

    with open(
        os.path.join(docs_dir, "docs-config.json"), "w", encoding="utf-8"
    ) as handle:
        handle.write(DOCS_CONFIG)
    scripts_dir = os.path.join(args.out, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    shutil.copyfile(
        os.path.join(REPO, "scripts", "docs.py"), os.path.join(scripts_dir, "docs.py")
    )

    total = len([n for n in os.listdir(docs_dir) if n.endswith(".md")])
    print(
        f"navigation-breadth: built {total} docs (gold={GOLD_NAME}, decoys={list(DECOY_DOCS)}) in {docs_dir}"
    )


if __name__ == "__main__":
    main()
