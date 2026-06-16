# Add or remove a harness

`/foundry:update`, asked to add or remove a harness from a consumer repo, changes only
the manifest's `harnesses` set and that harness's shim — never the rest of the
interview. Idempotent: a harness already present (for add) or absent (for remove) is a
no-op.

## Add

1. Emit only the harness's shim:
   - **claude-code** → `ln -s AGENTS.md CLAUDE.md` when `CLAUDE.md` is absent.
   - a harness that reads `AGENTS.md` natively (Codex, Gemini, …) → no shim.
2. Add it to `.foundry/manifest.json` `harnesses`.
3. Run the canonical gate (no-regression); ask before committing.

## Remove

1. Delete only that harness's shim (e.g. `CLAUDE.md` for claude-code); leave `AGENTS.md`
   and every shared file.
2. Remove it from `harnesses`. Refuse to remove the last harness — a repo targets at
   least one.
