> **Status:** Done (2026-07-03) — tracked on the [board](../../ROADMAP.md).

# foundry-cli-shim — tasks

Waves are ordered; tasks within a wave are independent. Each task names the gate that
proves it.

## Wave 1 — the shim template + self-host copy

- **T1** Write `src/foundry/templates/verbatim/.foundry/bin/foundry` (executable, marker
  `foundry-shim v1`): self-host-aware forwarder (D1). Add foundry's byte-identical copy
  `.foundry/bin/foundry` + its manifest entry. *Gate: `scripts/check-byte-identity.sh`
  (self-host); a shim-behavior test — self-host branch runs the local tree, consumer branch
  reads the pin, missing pin fails.*

## Wave 2 — the migration (the convention break)

- **T2** `src/foundry/materializer/migrations/m006_cli_shim.py`: `applies` on conv 5 + shim
  absent; `apply` installs the shim (chmod +x, manifest entry), rewrites `.githooks/pre-push`
  and CI gate lines to `.foundry/bin/foundry gate`, bumps `conventionVersion` 6. Register in
  `update._migrations`; add the registry-head row; bump foundry manifest to 6. *Gate:
  `tests/test_migration_m006` (fixture conv-5 repo → shim installed, hook pin-free, conv 6,
  idempotent); `check-gate-tools.sh` (head == manifest).*

## Wave 3 — bootstrap the shim by default

- **T3** Bootstrap writes the pre-push as `exec .foundry/bin/foundry gate` (pin-free); the
  shim installs via the existing verbatim `rglob`; `config.toml` keeps the pin. *Gate:
  `tests/test_bootstrap` — a fresh repo's hook is pin-free and `.foundry/bin/foundry` exists
  and is executable.*

## Wave 4 — close

- **T4** Knowledge: glossary term **CLI shim** (or extend **Pinned run**); `log.md`; board
  row. Note the conv-6 claim so `decision-taxonomy` renumbers to 7. *Gate: `foundry gate`.*
- **T5** Fresh-context `code-review` (convention-break-with-migration check); apply
  findings. *Gate: `CODE_REVIEW: PASS`.*
