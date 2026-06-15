#!/usr/bin/env bash
# Build a minimal, faithful pre-OKF (convention 1) fixture for the migration eval.
#
# The migration acts on structure, markers, and paths — not on the old tools'
# internals (it deletes docs.py and copies the current knowledge.py). So the old
# verbatim tools are marker-stamped stubs; the concepts, config, manifest, gate, and
# AGENTS refs are faithful to a v1.0.0 bootstrap (cf. git 574f698, the clean docs/
# era). Self-contained — no coupling to git history at eval time.
#
# Usage:
#   build-migration-fixtures.sh <variant> <dest>
#     variant: okf | legacy | redgate
#       okf      — the base convention-1 repo (happy path)
#       legacy   — base minus .foundry-manifest.json (detection by structure)
#       redgate  — base whose app gate fails before migration (no-regression)
#     dest: empty/new directory to populate
#
# (dirty, discrimination, and chaining cases are set up by migration-eval.sh.)
set -euo pipefail

VARIANT="${1:?usage: build-migration-fixtures.sh <okf|legacy|redgate> <dest>}"
DEST="${2:?usage: build-migration-fixtures.sh <okf|legacy|redgate> <dest>}"
mkdir -p "$DEST"
cd "$DEST"

mkdir -p docs/.vitepress scripts .githooks .claude/rules specs

# ── concepts (old convention: kind: frontmatter) ─────────────────────────────
cat > docs/docs-config.json <<'EOF'
{
  "_foundry_seed": "docs-config v1",
  "kinds": ["reference", "architecture", "guide", "decision"],
  "lifecycles": ["current", "superseded", "historical"],
  "required_fields": ["title", "description", "kind"],
  "doc_globs": ["docs/*.md", "docs/**/*.md"],
  "exclude_substrings": ["/node_modules/", "/.vitepress/"],
  "exclude_prefixes": ["docs/crates/"],
  "exclude_paths": ["docs/README.md", "docs/index.md"],
  "skill_ref_prefixes": ["scripts/", "docs/", "specs/", ".claude/"]
}
EOF

cat > docs/glossary.md <<'EOF'
---
title: Glossary
description: The vocabulary contract for specs, code, and docs.
kind: reference
---

<!-- foundry-seed: glossary v1 -->

# Glossary

| Term | Definition | Replaces (now debt) |
|---|---|---|
| **widget** | The core domain object. | gizmo |
EOF

cat > docs/validation.md <<'EOF'
---
title: Validation
description: Every verification gate — command, what it catches, when it fires.
kind: reference
---

<!-- foundry-seed: validation v1 -->

# Validation

| Gate | Command | Trigger |
|---|---|---|
| Quick gate | `scripts/check-fast.sh` | pre-push + CI |
| Docs site build | `cd docs && npm run build` | CI |
EOF

cat > docs/coe-template.md <<'EOF'
---
title: COE template
description: Correction of Error — the fill-in record for a real failure.
kind: decision
---

<!-- foundry-seed: coe-template v1 -->

# Correction of Error — `<one-line title>`

*Copy this template to `docs/<slug>-coe.md`; keep the headings.*
EOF

cat > docs/README.md <<'EOF'
---
title: Docs index
description: How the docs are organized — the four kinds, the docs tool, the index.
kind: reference
---

<!-- foundry-seed: docs-readme v1 -->

# Docs

Browse by kind: `python3 scripts/docs.py list`. The four kinds are reference,
architecture, guide, decision.
EOF

cat > docs/index.md <<'EOF'
---
layout: home
title: fixture
description: A migration eval fixture.
hero:
  name: fixture
  tagline: A migration eval fixture.
---

<!-- foundry-seed: index v1 -->
EOF

cat > docs/ROADMAP.md <<'EOF'
---
title: Roadmap
description: The tracked kanban board — the single source of truth for status.
kind: reference
---

<!-- foundry-seed: roadmap v1 -->

# Roadmap

The idea pool is `docs/BACKLOG.md`. Specs live in `specs/<feature>/`. The
vocabulary contract is `docs/glossary.md`.

## Status Dashboard

### Epic 0 — first epic

| Work | Status | Spec | Depends on |
|---|---|---|---|
| Walking skeleton | Done | — | — |
EOF

cat > docs/BACKLOG.md <<'EOF'
---
title: Backlog
description: The idea pool — captured, not yet committed to the board.
kind: reference
---

<!-- foundry-seed: backlog v1 -->

# Backlog

An idea stays here until it becomes a card on `docs/ROADMAP.md`.
EOF

# ── verbatim tools: marker-stamped stubs (the migration deletes/replaces these) ─
cat > scripts/docs.py <<'EOF'
#!/usr/bin/env python3
# foundry-template: docs v1
"""docs — stub of the old knowledge tool (convention 1). `check` validates that
each curated docs/*.md concept has title/description/kind frontmatter."""
import glob, sys
def check():
    bad = []
    for path in glob.glob("docs/*.md"):
        if path.endswith(("README.md", "index.md")):
            continue
        head = open(path, encoding="utf-8").read().split("---")
        fm = head[1] if len(head) > 2 else ""
        for field in ("title:", "description:", "kind:"):
            if field not in fm:
                bad.append(f"{path}: missing {field}")
    if bad:
        print("\n".join(bad)); print("docs check: FAILED"); return 1
    print("docs check: OK"); return 0
if __name__ == "__main__":
    sys.exit(check() if sys.argv[1:2] == ["check"] else 0)
EOF

cat > scripts/test_docs.py <<'EOF'
#!/usr/bin/env python3
# foundry-template: test-docs v1
"""test-docs — stub unit test for the old docs tool (convention 1)."""
EOF

cat > scripts/board.sh <<'EOF'
#!/usr/bin/env bash
# foundry-template: board v1
# Render the board from docs/ROADMAP.md.
set -euo pipefail
echo "Board — docs/ROADMAP.md"
EOF

cat > scripts/install-hooks.sh <<'EOF'
#!/usr/bin/env bash
# foundry-template: install-hooks v1
set -euo pipefail
git config core.hooksPath .githooks
EOF

cat > scripts/worktree-retire.sh <<'EOF'
#!/usr/bin/env bash
# foundry-template: worktree-retire v1
# Promote durable notes to the tracked tree (docs/ROADMAP.md, specs/, docs/BACKLOG.md).
set -euo pipefail
echo "retire"
EOF

cat > .githooks/pre-push <<'EOF'
#!/usr/bin/env bash
# foundry-template: pre-push v1
set -euo pipefail
exec "$(dirname "$0")/../scripts/check-fast.sh"
EOF

cat > docs/.vitepress/config.ts <<'EOF'
// foundry-template: vitepress-config v1
import { defineConfig } from 'vitepress'
export default defineConfig({ title: 'fixture', srcExclude: ['**/node_modules/**'] })
EOF

cat > docs/package.json <<'EOF'
{
  "//": "foundry-template: vitepress-package v1",
  "name": "fixture-docs",
  "private": true,
  "scripts": { "build": "vitepress build", "dev": "vitepress dev" }
}
EOF

cat > docs/tsconfig.json <<'EOF'
{
  "//": "foundry-template: vitepress-tsconfig v1",
  "compilerOptions": { "module": "ESNext", "moduleResolution": "Bundler" }
}
EOF

# ── repo-owned: gate, AGENTS, rules, specs ───────────────────────────────────
cat > scripts/check-fast.sh <<'EOF'
#!/usr/bin/env bash
# The quick gate: lock-free; runs from .githooks/pre-push and CI.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== docs"
python3 scripts/docs.py check
echo "== app"
bash scripts/app-check.sh
echo "check-fast: PASS"
EOF

# app-check is repo-specific (the migration never touches it) — the independent
# gate signal for no-regression. redgate variant makes it fail before migration.
if [ "$VARIANT" = "redgate" ]; then
  printf '#!/usr/bin/env bash\nexit 1  # pre-existing failure, unrelated to migration\n' > scripts/app-check.sh
else
  printf '#!/usr/bin/env bash\nexit 0\n' > scripts/app-check.sh
fi

cat > AGENTS.md <<'EOF'
fixture — a migration eval fixture on the old docs/ convention.

## Commands

```bash
scripts/check-fast.sh        # the canonical gate: docs, app
python3 scripts/docs.py list # browse docs by kind
cd docs && npm run dev       # docs site
```

## Boundaries

- Use the `docs/glossary.md` vocabulary in records, APIs, and docs.

## Task tracking

`docs/ROADMAP.md` is the board. Specs live in `specs/<feature>/`; ideas in `docs/BACKLOG.md`.

## Deeper docs

`docs/README.md` indexes everything · `docs/glossary.md` · `docs/validation.md` · `specs/`.
EOF
ln -sf AGENTS.md CLAUDE.md

cat > .claude/rules/spec-conventions.md <<'EOF'
---
paths:
  - "specs/**/*.md"
  - "docs/glossary.md"
---

<!-- foundry-seed: spec-conventions v1 -->

# Spec conventions

## Names

- Use the canonical terms in `docs/glossary.md`.
EOF

cat > specs/README.md <<'EOF'
---
title: Spec format
description: How specs are written — requirements, design, tasks per feature.
kind: reference
---

<!-- foundry-seed: specs-readme v1 -->

# Specs

A feature's spec is `specs/<feature>/`. Status points to `../docs/ROADMAP.md`.
EOF

chmod +x scripts/*.sh scripts/*.py .githooks/pre-push

# ── manifest: pluginVersion 1.0.0, NO conventionVersion, real sha256s ─────────
if [ "$VARIANT" != "legacy" ]; then
  python3 - <<'PY'
import hashlib, json
entries = {
    ".githooks/pre-push": "pre-push",
    "scripts/install-hooks.sh": "install-hooks",
    "scripts/board.sh": "board",
    "scripts/worktree-retire.sh": "worktree-retire",
    "scripts/docs.py": "docs",
    "scripts/test_docs.py": "test-docs",
    "docs/package.json": "vitepress-package",
    "docs/tsconfig.json": "vitepress-tsconfig",
    "docs/.vitepress/config.ts": "vitepress-config",
}
files = {}
for path, template in entries.items():
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    files[path] = {"template": template, "version": 1, "sha256": sha}
manifest = {"pluginVersion": "1.0.0", "files": files}
json.dump(manifest, open(".foundry-manifest.json", "w"), indent=2)
open(".foundry-manifest.json", "a").write("\n")
PY
fi

echo "build-migration-fixtures: built '$VARIANT' at $DEST"
