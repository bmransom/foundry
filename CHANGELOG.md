# Changelog

## [0.1.1](https://github.com/bmransom/foundry/compare/v0.1.0...v0.1.1) (2026-06-16)


### Features

* **harness-agnostic:** add harness term and harness map ([3e3f563](https://github.com/bmransom/foundry/commit/3e3f563d001e5f706ef4424213328b75d776574c))
* **harness-agnostic:** bootstrap emits multi-harness setups (Axis B core) ([9c807a9](https://github.com/bmransom/foundry/commit/9c807a99c8e314fdfceebabd73bf2749361ba02d))
* **harness-agnostic:** convention-3 migration + harness add/remove (Axis C) ([5df7062](https://github.com/bmransom/foundry/commit/5df7062c5f1e41c702b3744d7f915f38382499ff))
* **harness-agnostic:** run foundry under Codex (Axis A) ([e311ba0](https://github.com/bmransom/foundry/commit/e311ba03853f391f9aa8c42a852e00c628ebb1d7))
* **update:** migrate repos across convention breaks ([39316bb](https://github.com/bmransom/foundry/commit/39316bb9380230f2cb555ed67a41862e945a5a7f))


### Bug Fixes

* **harness-agnostic:** Codex reads its own manifests, never .claude-plugin/ ([9610e90](https://github.com/bmransom/foundry/commit/9610e90ca6cd95faab4d6c56cd8625828921876a))
* **harness-agnostic:** drop redundant .codex-plugin manifests ([7917989](https://github.com/bmransom/foundry/commit/79179895ebb49feda11c4c606723360ccb30b41b))

## 0.1.0 (2026-06-15)


### ⚠ BREAKING CHANGES

* **knowledge:** concept frontmatter field is `type` (was `kind`); the tool is `scripts/knowledge.py` (was `docs.py`) with config `knowledge-config.json`.

### Features

* **evals:** navigation eval with cost/correctness visualization ([03592f8](https://github.com/bmransom/foundry/commit/03592f8b94694c3d7a12608cfa1bdbdec87bba9b))
* **knowledge:** align to OKF: type field, knowledge/concept vocabulary, generated index + log ([0f57589](https://github.com/bmransom/foundry/commit/0f57589c4880ae089601e4d7117e5e39f064cd7c))


### Bug Fixes

* **evals:** scope bootstrap-eval 'all' to bootstrap fixtures; run L3 on dispatch only ([e9efe52](https://github.com/bmransom/foundry/commit/e9efe52a1294b4e77ba697cdd9f6bf4b6955f33d))


### Miscellaneous

* adopt 0.x versioning until the knowledge format stabilizes ([a7069a3](https://github.com/bmransom/foundry/commit/a7069a3fcb81551498b15a07f0ae727bf07bcc2e))
