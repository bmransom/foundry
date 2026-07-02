"""Gate suite (design D5, AC-5.2): the code-owned check set `foundry gate` runs.

Each submodule ports one v1 gate tool's CHECK behavior (`src/foundry/templates/
verbatim/scripts/{check-board,prose-lint,knowledge}.py`) into an importable `check(repo_root)
-> (ok, findings)` function — no sys.exit, no argv parsing. `suite.run` composes them with
the repo's `[gate].commands`.
"""
