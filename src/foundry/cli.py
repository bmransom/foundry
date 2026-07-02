"""Foundry CLI entry point: argparse dispatch over the driver's subcommands."""

import argparse
import sys

from foundry import __version__

# Stage-0 stubs: Wave 1+ tasks (T7 run, T11 gate, T12 doctor, T15/T16
# bootstrap/update, T17 eval, T18 review) fill these in. `runs` covers
# AC-4.3/AC-4.4.
SUBCOMMANDS = ["run", "gate", "doctor", "runs", "eval", "review", "bootstrap", "update"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="foundry")
    parser.add_argument(
        "--version", action="version", version=f"foundry {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")
    for name in SUBCOMMANDS:
        subparsers.add_parser(name)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    print(f"foundry {args.command}: not yet implemented", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
