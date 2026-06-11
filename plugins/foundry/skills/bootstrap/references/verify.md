# Verify — the acceptance checklist

Reference for bootstrap phase 5. Run every command and paste its output. A
claim without pasted output does not pass.

## 1 · File inventory (AC-1.1)

```bash
ls -la AGENTS.md CLAUDE.md .githooks/pre-push .github/workflows/check-fast.yml
ls scripts docs docs/.vitepress specs features .claude/rules
```

Expected — every row present (plus whatever the repo already had):

| Path | Class |
|---|---|
| `AGENTS.md` · `CLAUDE.md -> AGENTS.md` (symlink) | generated |
| `docs/{README,index,ROADMAP,BACKLOG,glossary,validation,coe-template}.md` · `docs/docs-config.json` | seeds, filled |
| `docs/.vitepress/{config.ts,site.json}` · `docs/{package.json,tsconfig.json}` | verbatim (`site.json` is a seed) |
| `specs/README.md` · `features/README.md` · `.claude/rules/spec-conventions.md` | seeds |
| `features/<name>.feature` + its runner wiring | generated |
| `scripts/{docs.py,test_docs.py,board.sh,install-hooks.sh,worktree-retire.sh}` · `.githooks/pre-push` | verbatim |
| `scripts/check-fast.sh` · `.github/workflows/check-fast.yml` | generated |
| `scripts/verify.sh` (+ lock) | generated — only when an expensive validation exists |

Version markers (AC-1.6):

```bash
grep -rl 'foundry-template:' scripts .githooks docs | sort
```

Expected: every verbatim copy above appears.

## 2 · Self-verification (AC-1.2)

| Check | Command | Expected final output |
|---|---|---|
| Hooks installed | `scripts/install-hooks.sh && git config core.hooksPath` | `hooks installed (core.hooksPath=.githooks, N hook(s))` · `.githooks` |
| Docs site builds | `cd docs && npm install && npm run build` | vitepress `build complete` |
| Walking skeleton | the feature-runner command `check-fast.sh` names | the Scenario passes |
| The quick gate | `scripts/check-fast.sh` | `check-fast: PASS` |

Paste all four outputs into the reply.

## 3 · Discrimination probe

Never ship a gate you have not seen fail — a vacuous gate self-certifies. Seed
one failing check the gate must catch:

| Stack | Seed |
|---|---|
| Rust | `tests/seeded_defect.rs`: `#[test] fn seeded_defect() { assert!(false); }` |
| Python | `tests/test_seeded_defect.py`: `def test_seeded_defect(): assert False` |
| TS/JS | a test asserting `expect(true).toBe(false)` |

```bash
scripts/check-fast.sh; echo "exit=$?"
```

Expected: the gate output names the failure and `exit=1`. Paste it. Delete the
seed, re-run, paste the clean `check-fast: PASS`.

## 4 · Commit — ask first

```bash
git status
```

Review every new and modified path — nothing unexplained; build artifacts
gitignored; `docs/package-lock.json` tracked. Propose the commit with explicit
paths — never `git add -A`:

```bash
git add AGENTS.md CLAUDE.md .gitignore .githooks .github/workflows/check-fast.yml \
  .claude docs features scripts specs/README.md <the runner wiring: tests/… or the cucumber config> \
  <stack manifests: Cargo.toml / pyproject.toml / package.json>
git commit -m "feat: bootstrap the foundry engineering setup"
```

**Ask before running the commit.** Report alongside the proposal any
pre-existing file Inspect merged or skipped.
