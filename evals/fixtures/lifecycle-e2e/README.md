# lifecycle-e2e — full-workflow dogfood eval

> Layer-4, on-demand, heavyweight. **Not** in `check-fast`. The point is to drive
> Foundry's *entire* workflow from nothing and let the failures show where the
> **workflow** (not the example app) needs work.

## What it does (one run)

1. **Fresh repo** — a brand-new empty git repo in a temp dir (nothing carried over).
2. **Install foundry** — make the plugin available and run the **bootstrap** skill
   with the canned poker interview answers below. Done once **per harness**.
3. **Drive the lifecycle** — for each feature in the roadmap, a **headless agent**
   runs the `code` lifecycle stages (Frame → Spec → Plan → Build → Verify →
   Knowledge → Review → Finish) using the canned inputs.
4. **Verify the gates** — the generated repo's `check-fast` is green, every
   feature has a passing Scenario, and each card records a gate PASS.
5. **Assert the app** — run the CPU-vs-CPU sim (below) and check it completes.
6. **Collect artifacts** — copy the generated repo to
   `evals/results/lifecycle-e2e-<harness>-<stamp>/` for human review.
7. **Matrix** — repeat for `{claude-code, codex}` to validate harness-agnosticism.

## The eval's actual signal: workflow friction (app-agnostic)

The deliverable is **not** "did the poker app work" — it is a per-stage report of
where the headless agent **completed the gate unaided / needed a retry / produced a
wrong artifact / got stuck**. Each friction point is a candidate **foundry**
improvement (a gate, rule, skill clarification, or eval), never a poker-specific
patch. Grade the workflow, not the app.

## The fixture — Texas Hold'em (engine + CPU sim + HTTP API + minimal browser UI)

### Canned bootstrap interview answers
1. **Project:** a Texas Hold'em poker engine with a backend HTTP API, computer
   players, and a minimal browser UI for a human to play turn-based hands.
2. **Domain terms (+ debt):** hand, hole cards, community cards, board, pot,
   side pot, blind, betting round (preflop/flop/turn/river), action (fold/check/
   call/bet/raise), showdown. Debt: "card value" → **rank**; "AI" → **CPU player**.
3. **Vocabulary polarity:** embrace the domain (a product).
4. **API surface:** yes — an HTTP API (used by the future browser UI).
5. **Gate commands:** the stack's test + lint + build (discovered at bootstrap).
6. **Parallel agents:** yes.
7. **Unit of work for logging:** a **hand**.
8. **First epic:** "Playable Texas Hold'em vs computer players."

### Feature roadmap (each driven through the full lifecycle)
`deck-and-cards` → `hand-evaluation` (best 5 of 7) → `betting-rounds` (the action
state machine) → `pot-and-side-pots` → `cpu-player` (a legal-action policy) →
`turn-based-loop` (deal → bet → advance → showdown) → `sim-runner`
(`sim --hands N` plays CPU-vs-CPU) → `http-api` (serve game state + actions over
HTTP) → `web-ui` (a minimal browser client to play a hand against the CPU players).

### Acceptance (the app assertion, run by the eval)
**Automated:** `sim --hands N` completes with, for every hand: only **legal**
actions taken, **chips conserved** (sum constant), exactly **one** pot winner (or a
correct split), and no crash; **and** an HTTP smoke plays one hand end-to-end
through the API (start → legal actions → showdown) with the server up. That is the
automatable PASS. **Human:** the eval then serves the app so the maintainer can
play a hand against the CPU players in the browser as part of artifact review.

## Beyond v1
Persistence, multi-table, a richer UI, more harnesses — only if the core E2E proves
stable. v1 already covers engine + CPU sim + HTTP API + a minimal playable browser UI.

## Status
v1 scaffold. `evals/harness/lifecycle-e2e-eval.sh --plan` prints the staged plan.
The headless drive/verify/assert/collect steps are built incrementally (the heavy,
long-running part). Per-iteration, the maintainer reviews the artifacts and feeds
workflow gaps back into foundry.
