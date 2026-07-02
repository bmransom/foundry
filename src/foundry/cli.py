"""Foundry CLI entry point: argparse dispatch over the driver's subcommands."""

import argparse
import sys
from pathlib import Path

from foundry import __version__

# Stub subcommands: later tasks (T18 review) fill these in.
# `run`, `runs`, `gate`, `doctor`, `bootstrap`, `update`, and `eval` are wired below.
STUB_SUBCOMMANDS = ["review"]

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

    subparsers.add_parser("gate", help="run the gate suite (AC-5.2)")
    subparsers.add_parser("doctor", help="verify the repo's foundry state (AC-6.1)")

    boot = subparsers.add_parser(
        "bootstrap", help="materialize the foundry setup into this repo (AC-7.1)"
    )
    intake = boot.add_mutually_exclusive_group(required=True)
    intake.add_argument(
        "--answers", metavar="JSON_FILE", default=None,
        help="materialize from a JSON answers file (deterministic path)",
    )
    intake.add_argument(
        "--interview", action="store_true",
        help="gather answers by interviewing through the routed harness (AC-7.2)",
    )
    boot.add_argument(
        "--harness", default=None,
        help="harness to run the interview through (default: shipped routing)",
    )
    boot.add_argument(
        "--model", default=None, help="model override for the interview",
    )

    upd = subparsers.add_parser(
        "update", help="re-sync templates and cross convention breaks (AC-7.3)"
    )
    upd.add_argument(
        "--dry-run", action="store_true",
        help="print the update plan without writing",
    )

    ev = subparsers.add_parser(
        "eval", help="run eval fixtures across a harness×model matrix (AC-8.1/8.2)"
    )
    ev.add_argument(
        "--matrix", required=True, metavar="SPEC",
        help="comma-separated cells, harness:model[:effort] (e.g. claude-code:claude-sonnet-5)",
    )
    ev.add_argument(
        "--fixture", default=None, metavar="NAME",
        help="run only the named fixture pair (default: all under evals/fixtures/matrix)",
    )
    ev.add_argument(
        "--dry-run", action="store_true",
        help="list the cells×fixtures that would run, without calling a harness",
    )

    for name in STUB_SUBCOMMANDS:
        subparsers.add_parser(name)
    return parser


def _run(args) -> int:
    from foundry.board import BoardError
    from foundry.driver.machine import AutonomyError
    from foundry.run_command import RunNotFoundError, resume, run

    if args.resume:
        try:
            result = resume(args.resume, repo_root=Path.cwd())
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


def _gate(args) -> int:
    from foundry.gate.suite import run as run_suite

    ok, lines = run_suite(Path.cwd())
    for line in lines:
        print(line)
    return 0 if ok else 1


def _doctor(args) -> int:
    from foundry.doctor import run as run_doctor

    ok, lines = run_doctor(Path.cwd())
    for line in lines:
        print(line)
    return 0 if ok else 1


def _bootstrap(args) -> int:
    from foundry import adapters
    from foundry.config import Config
    from foundry.materializer.bootstrap import Answers, BootstrapError, bootstrap, interview

    repo_root = Path.cwd()
    try:
        if args.answers:
            answers = Answers.from_json_file(args.answers)
        else:
            config = Config.load(repo_root)
            route = config.route_for("spec", harness=args.harness, model=args.model)
            adapter = adapters.load(route.harness or "claude-code")
            answers = interview(adapter, route, str(repo_root))
    except (BootstrapError, adapters.AdapterError) as e:
        print(f"foundry bootstrap: {e}", file=sys.stderr)
        return 2

    ok, lines = bootstrap(repo_root, answers)
    for line in lines:
        print(line)
    return 0 if ok else 1


def _update(args) -> int:
    from foundry.materializer.update import run as run_update

    for line in run_update(Path.cwd(), dry_run=args.dry_run):
        print(line)
    return 0


def _eval(args) -> int:
    from foundry.eval_command import EvalError, run_matrix

    try:
        ok, lines = run_matrix(
            matrix=args.matrix, repo_root=Path.cwd(),
            fixture=args.fixture, dry_run=args.dry_run,
        )
    except EvalError as e:
        print(f"foundry eval: {e}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0 if ok else 1


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
    if args.command == "gate":
        return _gate(args)
    if args.command == "doctor":
        return _doctor(args)
    if args.command == "bootstrap":
        return _bootstrap(args)
    if args.command == "update":
        return _update(args)
    if args.command == "eval":
        return _eval(args)
    print(f"foundry {args.command}: not yet implemented", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
