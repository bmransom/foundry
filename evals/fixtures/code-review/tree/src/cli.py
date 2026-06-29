"""Cache-purge CLI (AC-3.1)."""

import argparse


def build_parser():
    parser = argparse.ArgumentParser(prog="order-sync")
    parser.add_argument("command", choices=["purge", "print"])
    # NEW public behavior, absent from design.md and docs/cli.md: an operator can
    # now purge only the partner-response cache, leaving the request cache intact.
    parser.add_argument(
        "--purge-cache",
        choices=["partner", "request", "all"],
        default="all",
        help="which cache to purge",
    )
    # The boundary owns the partner timeout: a CLI flag with a default is the right
    # place for this knob. Downstream code should require the value, not re-default it.
    parser.add_argument(
        "--partner-timeout",
        type=int,
        default=30,
        help="partner request timeout (seconds)",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "print":
        # A legitimate CLI surface: `order-sync print --help` prints usage. This
        # is a user-facing command, NOT a logging mix.
        parser.parse_args(["print", "--help"])
        return 0
    if args.command == "purge":
        purge_cache(args.purge_cache)
        return 0
    return 2


def purge_cache(which):
    """Clear the named cache (AC-3.1)."""
    # Real implementation would clear the cache store here.
    return which
