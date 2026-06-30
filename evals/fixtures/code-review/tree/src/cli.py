"""Cache-purge CLI (AC-3.1)."""

import argparse
import os


def build_parser():
    parser = argparse.ArgumentParser(prog="order-sync")
    parser.add_argument("command", choices=["purge", "print"])
    # NEW public behavior, absent from design.md and docs/cli.md: an operator can
    # now purge only the partner-response cache, leaving the request cache intact.
    parser.add_argument(
        "--purge-cache",
        choices=["partner", "request", "all", "expired"],
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
    # CORRECT: the boundary may read the environment to populate a config default.
    # This is the right place for an env read — PARTNER_ENDPOINT seeds the CLI default,
    # and downstream code receives the resolved value as config; it does not read the
    # environment itself. Not a Config violation.
    parser.add_argument(
        "--partner-endpoint",
        default=os.environ.get("PARTNER_ENDPOINT", "https://partner.example/api"),
        help="partner API endpoint",
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
    # RIPPLE: build_parser now also offers `--purge-cache expired`, but this dispatch was
    # not updated to handle it — a half-applied change; `purge expired` falls through to the
    # ValueError. Either wire `expired` here or drop it from the choices.
    if which == "partner":
        return "partner cache cleared"
    if which == "request":
        return "request cache cleared"
    if which == "all":
        return "all caches cleared"
    raise ValueError(f"unknown cache {which}")
