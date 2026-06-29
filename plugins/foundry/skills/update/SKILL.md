---
name: update
description: Use when explicitly asked to update, sync, or refresh the foundry
  templates in a bootstrapped repo, or to migrate one across a convention break
  Templates and convention migrations only — skills and agents
  propagate with the plugin install, no per-repo action.
---

# Update

Re-sync the repo's installed templates with the plugin's, first crossing any
**convention break** the repo is behind (a release that renamed templates, moved
directories, or changed frontmatter). Templates ship at `<plugin root>/templates/`
— `verbatim/` (byte-exact, manifest-tracked) and `seeds/` (repo-owned). Migrations
live in `references/migrations/`.

Copy into your reply; check off as you go. A gate is a **prohibition**: do not start
a later phase until the prior gate is met.

- [ ] **1 Read state** — `.foundry-manifest.json`; absent → Legacy mode. GATE: no writes before the report.
- [ ] **2 Detect & plan migrations** — place the repo's convention; build the chain to the registry head. GATE: clean tree; dry-run report; no writes.
- [ ] **3 Migrate** — on a branch, run each migration in order, re-checking between steps. GATE: stop on the first failed step.
- [ ] **4 Compare verbatim** — classify every template. GATE: classification only, no copies.
- [ ] **5 Compare seeds** — `foundry-seed:` versions, repo vs plugin. GATE: never touch a repo seed.
- [ ] **6 Report** — the verdict table; then apply refreshes and new installs. GATE: no write before the table.
- [ ] **7 Verify** — migration checks green; canonical gate not regressed; manifest current. GATE: no commit or merge without a pasted PASS and go-ahead.

## 1 · Read state

Read `.foundry/manifest.json` (legacy fallback: a top-level `.foundry-manifest.json`) — the
shape bootstrap writes and Legacy backfills: `pluginVersion`, `conventionVersion`, `harnesses`,
and `files` (each installed verbatim file's `template` / `version` / `sha256`).

`conventionVersion` is the layout the repo is on; absent → §2 places it by detection.
`harnesses` is the recorded target set; add or remove one per `references/add-harness.md`. No manifest → Legacy mode.

## 2 · Detect & plan migrations

Read `references/migrations/README.md` — the registry, ordered by convention version.
The repo's convention is the manifest `conventionVersion`, else the earliest whose
detector fires; the plugin's is the registry head. The chain is every migration with
`repo < convention ≤ head`, ascending — empty → skip to §4.

GATE: refuse on a dirty tree (tell the caller to commit a baseline); place the repo
by structure, never guess; then **dry-run report** the whole chain, writing nothing.

## 3 · Migrate

**Preflight — this is how the branch is created; never branch by hand:**
`bash "<base dir>/references/migrations/preflight.sh" <head-id>`. It refuses a dirty
tree (nonzero exit → STOP: relay its message and end; do not commit, stash, or work
around it) and, on a clean tree, creates and switches to `foundry/migrate-<head-id>`.
All writes land on that branch; leave it for the caller to merge. Record the gate's
current result as the **baseline**.

Run each migration ascending, per its playbook (`references/migrations/<id>.md`): its
primitives exactly, its judgment by reading the repo; regenerate `index.md` /
`log.md`; re-run the structure and frontmatter checks. A step that fails **stops the
chain** — prior steps stay, report which failed, do not continue. After the last,
stamp `conventionVersion = head`. The phases below then confirm current and catch any
refresh unrelated to the break.

## 4 · Compare verbatim

Per template under `verbatim/`: its marker version (`foundry-template: <name>
v<N>`) vs the manifest entry's version.

| Finding | Verdict | Action at apply time |
|---|---|---|
| same version | **current** | skip |
| newer; `shasum -a 256` of the repo file equals the manifest hash | **pristine** | refresh: copy byte-exact; re-record name, version, hash |
| newer; hash differs | **customized** | Leave the file. Flag two diffs: the template changelog (old → new template) and the local change (old template → repo file). Recover the old pristine content from git history; if gone, show only the changelog and flag it unrecoverable. |
| no manifest entry | **new** | install like bootstrap's Copy: byte-exact, marker included, scripts executable; add the manifest entry |

Manifest hashes cover the installed content *including* its marker — hash what is on
disk at install or refresh time.

## 5 · Compare seeds

Seeds are repo-owned; divergence is the point. Compare the seed marker repo vs plugin
— `foundry-seed: <name> v<N>` in markdown, the `"_foundry_seed"` key in JSON. Plugin
newer → **announced**: show the repo-copy-vs-plugin-seed diff so the repo can adopt
what it wants. Never write to a repo seed.

## 6 · Report

One table before anything is written — a row per template: path | class (verbatim /
seed) | verdict (current / refreshed / customized / new / announced; Legacy adds
pristine-backfilled / needs-review). Then apply refreshes and new installs only: copy
byte-exact, keep scripts executable, update each manifest entry.

**Gate-sync.** A verbatim script with a `# foundry-gate-tool:` marker belongs in the gate. After installs, grep
the repo's gate (the command `AGENTS.md` Commands names) for each installed marked tool's basename; flag every
unwired one with its marker line as the snippet, offer to add it on go-ahead, never silently edit the gate.

## 7 · Verify

Migration checks first: `python3 scripts/knowledge.py check`, each applied migration's
residue scan (per its playbook §Self-verify), manifest-sha match — all green. Then the
repo's canonical gate (the command AGENTS.md Commands names): require **no regression**
against the §3 baseline — a gate already red before is reported, not blamed. Revert and
flag any refresh that broke a check. Set the manifest's plugin version to the installed
plugin's. Review `git status`, propose the commit with explicit paths, **ask before
committing**, and leave the migration branch for the caller to merge.

## Legacy mode — pre-manifest repo

No manifest means "customized" vs "older pristine" is undecidable from content alone
— say so; never guess. A no-manifest repo is also pre-`conventionVersion`: §2 places
its convention by detection, so a Legacy repo on the old layout still migrates.

Per verbatim file, compare content modulo the marker against the current template
(strip marker lines with `grep -vF 'foundry-template:'` both sides): identical →
record pristine at the current version; different → flag for review with the diff, no
entry, no write. Seeds need no manifest — run §5 as usual.

Write `.foundry/manifest.json` from the verified entries plus the plugin and
convention versions, then finish with §7. The backfill is a write — it needs the
pasted PASS and go-ahead. Refreshes wait for the next run, in manifest mode above.
