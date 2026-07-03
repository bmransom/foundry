Feature: foundry run drives a card through the lifecycle
  `foundry run <card-id>` resolves the card from the board, creates or reuses its
  worktree off the default branch, walks the lifecycle stages behind code-evaluated
  gates, and records a run ledger — never committing to the default branch (AC-1.1,
  AC-1.8). This is a process contract for the `foundry run` entrypoint.

  Scenario: A bug-fix run completes on its own branch
    Given a repository whose board lists card "wclip-paste"
    And the default branch has one commit
    When I run "foundry run wclip-paste --path bug-fix"
    Then a worktree "wt/wclip-paste" on branch "card/wclip-paste" exists
    And the run ledger records "run_started" first and "run_completed" last
    And the recorded entry path is "bug-fix"
    And the default branch has no new commits

  Scenario: An unknown card is rejected with a near match
    Given a repository whose board lists card "wclip-paste"
    When I run "foundry run wclip-past"
    Then the command fails
    And the error names "wclip-paste" as a near match

  Scenario: An interrupted run resumes from its last recorded boundary
    Given a repository whose board lists card "wclip-paste"
    And a run of "wclip-paste" halted after stage "frame" completed
    When I run "foundry run --resume <run-id>"
    Then the ledger records "run_resumed"
    And the run continues from the stage after "frame"
    And no completed stage appears twice in the ledger

  Scenario: Resuming an unknown run id fails
    Given a repository whose board lists card "wclip-paste"
    When I run "foundry run --resume does-not-exist"
    Then the command fails
    And the error lists the known run ids

  Scenario: Resuming an already-complete run is a no-op
    Given a repository whose board lists card "wclip-paste"
    And a run of "wclip-paste" has already reached "run_completed"
    When I run "foundry run --resume <run-id>"
    Then the command succeeds
    And the output says "already complete"

  Scenario: An interactive run defers to the harness, then gates on exit
    Given a repository whose board lists card "wclip-paste"
    When I run "foundry run wclip-paste --path bug-fix --interactive"
    Then the routed harness's interactive command runs inside "wt/wclip-paste" with stdio inherited
    And the stage gate — not the session's exit code alone — decides the transition

  Scenario: A failed gate's evidence reaches the retried attempt
    Given a repository whose board lists card "wclip-paste"
    And the build gate fails on the first attempt and passes on the second
    When I run "foundry run wclip-paste --path bug-fix"
    Then the first build attempt receives no feedback
    And the second build attempt's feedback names the failed gate, the failed attempt, and its evidence
    And each "gate_evaluated" event records a capped tail of the attempt's returned text
