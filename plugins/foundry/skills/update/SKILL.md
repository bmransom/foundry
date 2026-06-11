---
name: update
description: Use when explicitly asked to update, sync, or refresh the foundry
  templates in a bootstrapped repo (/foundry:update). Templates only — skills
  and agents propagate with the plugin install itself, no per-repo action.
---

# Update

Re-sync the repo's installed templates with the plugin's current ones.
Templates ship with the plugin at `<base dir>/../../templates/` — `verbatim/`
(byte-exact, manifest-tracked) and `seeds/` (repo-owned, announce only).

Copy into your reply; check off as you go. A gate is a **prohibition**: do not
start a later phase until the prior gate is met.

- [ ] **1 Read state** — `.foundry-manifest.json`; absent → Legacy mode (below). GATE: no file writes before the full comparison report.
- [ ] **2 Compare verbatim** — classify every plugin template: current, refresh, customized, or new. GATE: classification only — no copies yet.
- [ ] **3 Compare seeds** — `foundry-seed:` marker versions, repo vs plugin. GATE: never touch a repo seed.
- [ ] **4 Report** — the verdict table in the reply; then apply refreshes and new installs. GATE: no write before the table.
- [ ] **5 Verify** — the repo's canonical gate green; manifest current. GATE: no commit without a pasted PASS and the caller's go-ahead.

## 1 · Read state

Read `.foundry-manifest.json` at the repo root — the canonical shape, written
by bootstrap and backfilled by Legacy mode:

```json
{ "pluginVersion": "0.1.0",
  "files": { "scripts/board.sh": { "template": "board", "version": 1, "sha256": "<hex>" } } }
```

Absent → the repo predates the manifest; switch to Legacy mode below. Phases
2–3 are read-only; nothing is written until the report (4) is in the reply.

## 2 · Compare verbatim

Per template under `verbatim/`: its marker version (`foundry-template: <name>
v<N>`) vs the manifest entry's version.

| Finding | Verdict | Action at apply time |
|---|---|---|
| same version | **current** | skip |
| newer; `shasum -a 256` of the repo file equals the manifest hash | **pristine** | refresh: copy byte-exact; re-record name, version, hash |
| newer; hash differs | **customized** | leave the file alone; flag with both diffs — the template changelog (old → new template) and the local customization (old template → repo file); the old pristine content is in the repo's git history |
| no manifest entry | **new** | install like bootstrap's Copy: byte-exact, marker included, scripts executable; add the manifest entry |

Manifest hashes cover the installed content *including* its marker — hash what
is on disk at install or refresh time.

## 3 · Compare seeds

Seeds are repo-owned; divergence is the point. Compare the seed marker in the
repo file vs the plugin's copy — `foundry-seed: <name> v<N>` in markdown, the
`"_foundry_seed"` key in JSON seeds. Plugin newer → **announced**: show the
repo-copy-vs-plugin-seed diff so the repo can adopt what it wants. Never write
to a repo seed.

## 4 · Report

One table before anything is written — a row per template: path | class
(verbatim / seed) | verdict (current / refreshed / customized / new /
announced; Legacy mode adds pristine-backfilled / needs-review).

Then apply: refreshes and new installs only — copy byte-exact from the
template, keep scripts executable, update each entry in the manifest.

## 5 · Verify

Run the repo's canonical gate — the command AGENTS.md Commands names — and
paste the PASS. If a refresh broke the gate, revert that refresh, restore its
manifest entry, and flag it in the report. Set the manifest's plugin version to
the installed plugin's (`.claude-plugin/plugin.json`). Review `git status`,
propose the commit with explicit paths, and **ask before committing**.

## Legacy mode — pre-manifest repo

The plugin ships only current templates, so "locally customized" vs "older
pristine" is undecidable from content alone — say so in the report; never
guess.

Per verbatim file, compare content modulo the marker against the current
template — strip marker lines with `grep -vF 'foundry-template:'` on both
sides, the idiom foundry's own check-byte-identity.sh uses:

- identical → record as pristine at the current template version;
- different → flag for human review with the diff; no manifest entry, no write.

Seeds need no manifest — run 3 · Compare seeds as usual; announcements work in
Legacy mode too.

Write `.foundry-manifest.json` from the verified entries plus the plugin
version, report, and finish with 5 · Verify — the backfill is a write, so it
needs the pasted PASS and the caller's go-ahead like any other. Refreshes wait
for the next run, which proceeds in manifest mode above.
