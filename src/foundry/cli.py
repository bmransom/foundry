"""Foundry CLI entry point: argparse dispatch over the driver's subcommands."""

import argparse
import sys
from pathlib import Path

from foundry import __version__

# Stub subcommands: later tasks (T11 gate, T12 doctor, T15/T16 bootstrap/update,
# T17 eval, T18 review) fill these in. `runs` covers AC-4.3/AC-4.4.
STUB_SUBCOMMANDS = ["gate", "doctor", "runs", "eval", "review", "bootstrap", "update"]

RUN_PATHS = ("feature", "bug-fix", "refactor", "enhancement")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="foundry")
    parser.add_argument(
        "--version", action="version", version=f"foundry {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="drive a card through the lifecycle")
    run.add_argument("card_id", help="board card id to run")
    run.add_argument(
        "--path", choices=RUN_PATHS, default="feature",
        help="entry path (default: feature)",
    )

    for name in STUB_SUBCOMMANDS:
        subparsers.add_parser(name)
    return parser


def _run(args) -> int:
    from foundry.board import BoardError
    from foundry.driver.machine import AutonomyError
    from foundry.run_command import run

    try:
        result = run(args.card_id, repo_root=Path.cwd(), path=args.path)
    except (BoardError, AutonomyError) as e:
        print(f"foundry run: {e}", file=sys.stderr)
        return 2
    print(
        f"foundry run {args.card_id}: {result.outcome} "
        f"({result.run_id}); stages: {', '.join(result.stages_started)}"
    )
    return 0 if result.outcome == "completed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    if args.command == "run":
        return _run(args)
    print(f"foundry {args.command}: not yet implemented", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
