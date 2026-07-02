"""Foundry CLI entry point: argparse dispatch over the driver's subcommands."""

import argparse
import sys
from pathlib import Path

from foundry import __version__

# Stub subcommands: later tasks (T11 gate, T12 doctor, T15/T16 bootstrap/update,
# T17 eval, T18 review) fill these in. `runs` (AC-4.3/AC-4.4) is wired below.
STUB_SUBCOMMANDS = ["gate", "doctor", "eval", "review", "bootstrap", "update"]

RUN_PATHS = ("feature", "bug-fix", "refactor", "enhancement")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="foundry")
    parser.add_argument(
        "--version", action="version", version=f"foundry {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="drive a card through the lifecycle")
    run.add_argument(
        "card_id", nargs="?", default=None,
        help="board card id to run (omit with --resume)",
    )
    run.add_argument(
        "--path", choices=RUN_PATHS, default="feature",
        help="entry path (default: feature)",
    )
    run.add_argument(
        "--resume", metavar="RUN_ID", default=None,
        help="resume an interrupted run from its last ledger boundary (AC-1.6)",
    )
    run.add_argument(
        "--interactive", action="store_true",
        help="open the routed harness interactively for judgment stages (AC-1.5)",
    )
    run.add_argument(
        "--harness", default=None,
        help="override the routed harness for every judgment stage (AC-3.1)",
    )
    run.add_argument(
        "--model", default=None,
        help="override the routed model for every judgment stage (AC-3.1)",
    )
    run.add_argument(
        "--effort", default=None,
        help="override the routed reasoning effort for every judgment stage (AC-3.1)",
    )

    runs = subparsers.add_parser("runs", help="inspect the run ledger (AC-4.3/AC-4.4)")
    runs_sub = runs.add_subparsers(dest="runs_command")
    runs_sub.add_parser("list", help="list past runs with outcome and cost")
    show = runs_sub.add_parser("show", help="print one run's stage table")
    show.add_argument("run_id")

    for name in STUB_SUBCOMMANDS:
        subparsers.add_parser(name)
    return parser


def _run(args) -> int:
    from foundry.board import BoardError
    from foundry.driver.machine import AutonomyError
    from foundry.run_command import RunNotFoundError, resume, run

    if args.resume:
        try:
            result = resume(
                args.resume, repo_root=Path.cwd(),
                harness=args.harness, model=args.model, effort=args.effort,
            )
        except (BoardError, AutonomyError, RunNotFoundError) as e:
            print(f"foundry run --resume: {e}", file=sys.stderr)
            return 2
        if result.outcome == "already_complete":
            print(f"foundry run --resume {args.resume}: already complete")
            return 0
        print(
            f"foundry run --resume {args.resume}: {result.outcome} "
            f"({result.run_id}); stages: {', '.join(result.stages_started)}"
        )
        return 0 if result.outcome == "completed" else 1

    if not args.card_id:
        print("foundry run: card_id is required unless --resume is given", file=sys.stderr)
        return 2

    try:
        result = run(
            args.card_id, repo_root=Path.cwd(), path=args.path, interactive=args.interactive,
            harness=args.harness, model=args.model, effort=args.effort,
        )
    except (BoardError, AutonomyError) as e:
        print(f"foundry run: {e}", file=sys.stderr)
        return 2
    print(
        f"foundry run {args.card_id}: {result.outcome} "
        f"({result.run_id}); stages: {', '.join(result.stages_started)}"
    )
    return 0 if result.outcome == "completed" else 1


def _runs(args) -> int:
    from foundry.runs_command import RunNotFoundError, list_lines, show_lines

    repo_root = Path.cwd()
    if args.runs_command == "list":
        for line in list_lines(repo_root):
            print(line)
        return 0
    if args.runs_command == "show":
        try:
            lines = show_lines(repo_root, args.run_id)
        except RunNotFoundError as e:
            print(f"foundry runs show: {e}", file=sys.stderr)
            return 2
        for line in lines:
            print(line)
        return 0
    print("foundry runs: choose a subcommand (list|show)", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    if args.command == "run":
        return _run(args)
    if args.command == "runs":
        return _runs(args)
    print(f"foundry {args.command}: not yet implemented", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
