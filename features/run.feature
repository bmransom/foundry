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
