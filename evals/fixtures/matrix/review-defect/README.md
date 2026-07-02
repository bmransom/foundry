# review-defect — eval matrix fixture pair

A fixture pair for the `review` stage (T17, AC-8.2). Each twin is materialized into a
throwaway git repo: `base/` is committed as the baseline, `head/` replaces the working
tree, so `git diff HEAD` is the change the review stage reads.

- `seeded/` — the change introduces an off-by-one in `running_max` (drops the first
  index, so output length no longer matches input, violating AC-1) **and deletes the
  test that would catch it**. Expected verdict: `FAIL`.
- `clean/` — the twin: the same feature (handle `[]`, AC-2) done correctly, with the
  length test kept and an empty-input test added. Expected verdict: `PASS`.

Discrimination (AC-8.2): the seeded twin must FAIL **and** the clean twin must PASS.
One without the other is a non-discriminating cell.
