# Decision taxonomy — tasks

**Status:** Spec — tasks drafted (2026-06-29) — tracked on the [board](../../ROADMAP.md).

Waves are ordered; tasks within a wave are independent. Each task names the gate that proves it.
Tasks implement the approved **Option C** (genre-by-directory; `type` set `reference | architecture |
guide | dated`; `decision` retired to the `decisions/` folder). Implementation waits on the
`spec-review` pass (Wave 0).

## Wave 0 — approval

- **T0** Run `spec-review` in fresh context over these three files; apply findings. (Option C +
  `type: dated` selected by the maintainer 2026-06-29.) *Gate: `spec-review` CLEAN; recorded decision.*

## Wave 1 — config + lint (the mechanism, Option C)

- **T1** Replace `decision` with `dated` in the closed `type` set, add `"dated_types": ["dated"]` and
  the genre-directory set (`coes/`, `reviews/`, `decisions/`) to `knowledge/knowledge-config.json` and
  the seed. *Gate: `knowledge.py check` reads them; `test_knowledge.py` case.*
- **T2** Teach `knowledge.py` `discover`/`site_url` the genre directories: a `type: dated` concept's
  genre is its directory; map `knowledge/<genre>/x.md` to a clean URL without colliding with the
  crate-sync path logic. Bump the `knowledge` template marker + manifest `version`/`sha256`; mirror the
  verbatim copy byte-identical. *Gate: byte-identity; `check`; `test_knowledge.py`.*
- **T3** Add genre validation to `check`: a dated concept (type in `dated_types`) SHALL sit under a
  genre directory; flag one that does not (AC-2.2). *Gate: new `test_knowledge.py` case — a dated
  record at the knowledge root fails.*

## Wave 2 — surfacing + tooling

- **T4** Generalize the hardcoded `== "decision"` special-cases in `format_list` / `build_sidebar` to
  key on `dated_types`, not the literal type name. *Gate: `test_knowledge.py`.*
- **T5** Section dated output by genre directory in `list` / `index.md` / sidebar (AC-1.2), composing
  with the lifecycle de-emphasis to be delivered by the sibling card `okf-listing-fidelity` (the
  dependency landing first). *Gate: `test_knowledge.py`; regenerated `index.md`.*

## Wave 3 — prose + provenance (lockstep, AC-4.3)

- **T6** Update each dependent artifact on its axis (AC-4.3):
  - **templates/{verbatim,seeds}/ + self-host** — `knowledge-conventions` (the maintenance contract +
    the genre directories, AC-1.3 + AC-3.1), `coe-template`.
  - **plugin source** (ships with the plugin) — `okf.md` (Differences from OKF), the `knowledge` skill
    (home selection by genre directory, coherence AC-3.3).
  - **foundry's `knowledge/glossary.md`** — the **Type** entry (now the maintenance marker) + new
    **Evergreen** / **Dated** / **Genre** entries (search prior art, record provenance).

  *Gate: `prose-lint`; `check-skill-references`; `spec-review` on changed prose.*

## Wave 4 — migration + eval (the convention break)

- **T7** Write the migration playbook `references/migrations/decision-taxonomy.md`: detector (a
  `type: decision` concept, or config with no `dated_types`), idempotent transform (retype
  `decision`→`dated`, move each dated record into its genre directory, add `dated_types`),
  no-regression. Add
  the registry-head row and bump `conventionVersion`. *Gate: `check-gate-tools.sh` (registry head ==
  manifest); `migration-eval`.*
- **T8** Migrate foundry's own records: `coe-template.md` and `review-convergence-coe.md` →
  `knowledge/coes/`, retyped `type: decision` → `type: dated`. Regenerate `index.md`. *Gate: `check`;
  `index` fresh.*
- **T9** Add the discriminating eval case (AC-5.1): a dated record with no genre home fails the gate
  pre-fix, passes once filed under a genre directory; the evergreen/dated partition shows in generated
  output. *Gate: eval fails on the seeded defect.*

## Wave 5 — close

- **T10** Run `code-review` in fresh context (convention-break-with-migration check); apply findings.
  Set the card `Done` in the merging PR with the recorded `check-fast: PASS`. *Gate: `check-fast`;
  `code-review` PASS.*
