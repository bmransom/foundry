# Add or remove a harness

`/foundry:update`, asked to add or remove a harness from a consumer repo, changes only
the manifest's `harnesses` set and that harness's shim — never the rest of the
interview. Idempotent: a harness already present (for add) or absent (for remove) is a
no-op.

## Add

Run `python3 <plugin root>/scripts/harness-manage.py add <repo> <harness>`.

The helper creates only that harness's shim and updates `.foundry/manifest.json`:
**claude-code** gets `CLAUDE.md -> AGENTS.md` when absent; Codex and other harnesses
that read `AGENTS.md` natively get no shim.

## Remove

Run `python3 <plugin root>/scripts/harness-manage.py remove <repo> <harness>`.

The helper deletes only a Foundry-managed shim, leaves `AGENTS.md` and every shared
file untouched, reports a custom shim instead of deleting it, and refuses to remove
the last harness. Finish with `python3 <plugin root>/scripts/harness-manage.py
verify <repo>` so `harness-status.py` checks the remaining manifest harnesses without
editing the manifest.
