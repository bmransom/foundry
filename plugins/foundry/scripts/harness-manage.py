#!/usr/bin/env python3
"""Manage a consumer repo's Foundry harness set."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SHIM_BY_HARNESS = {
    "claude-code": "CLAUDE.md",
}


def load_manifest(repo: Path) -> dict[str, object]:
    manifest_path = repo / ".foundry/manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def write_manifest(repo: Path, manifest: dict[str, object]) -> None:
    manifest_path = repo / ".foundry/manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def manifest_harnesses(manifest: dict[str, object]) -> list[str]:
    harnesses = manifest.get("harnesses")
    if not isinstance(harnesses, list) or not all(
        isinstance(item, str) for item in harnesses
    ):
        raise SystemExit("manifest harnesses must be a string array")
    return list(harnesses)


def run_verify(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    manifest = load_manifest(repo)
    harnesses = manifest_harnesses(manifest)
    status_script = Path(__file__).resolve().with_name("harness-status.py")
    command = [sys.executable, str(status_script), str(repo), *harnesses]
    print(" ".join(command))
    if args.dry_run:
        return 0
    return subprocess.run(command, check=False).returncode


def run_add(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    manifest = load_manifest(repo)
    harnesses = manifest_harnesses(manifest)
    harness = args.harness

    if harness in harnesses:
        print(f"{harness} already present")
        return 0

    harnesses.append(harness)
    manifest["harnesses"] = harnesses
    message = ensure_shim(repo, harness)
    write_manifest(repo, manifest)
    print(message)
    print(f"added {harness}")
    return 0


def run_remove(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    manifest = load_manifest(repo)
    harnesses = manifest_harnesses(manifest)
    harness = args.harness

    if harness not in harnesses:
        print(f"{harness} already absent")
        return 0
    if len(harnesses) == 1:
        print("refuse to remove the last harness", file=sys.stderr)
        return 1

    message = remove_shim(repo, harness)
    manifest["harnesses"] = [item for item in harnesses if item != harness]
    write_manifest(repo, manifest)
    print(message)
    print(f"removed {harness}")
    return 0


def ensure_shim(repo: Path, harness: str) -> str:
    shim_name = SHIM_BY_HARNESS.get(harness)
    if shim_name is None:
        return f"{harness} reads AGENTS.md natively; no shim needed"

    shim = repo / shim_name
    if shim.exists() or shim.is_symlink():
        return f"shim {shim_name} already exists; left in place"
    os.symlink("AGENTS.md", shim)
    return f"created shim {shim_name}"


def remove_shim(repo: Path, harness: str) -> str:
    shim_name = SHIM_BY_HARNESS.get(harness)
    if shim_name is None:
        return f"{harness} has no shim"

    shim = repo / shim_name
    if not shim.exists() and not shim.is_symlink():
        return f"shim {shim_name} absent"
    if is_foundry_managed_shim(shim):
        shim.unlink()
        return f"removed shim {shim_name}"
    return f"custom shim {shim_name} left in place"


def is_foundry_managed_shim(shim: Path) -> bool:
    if not shim.is_symlink():
        return False
    return os.readlink(shim) == "AGENTS.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--dry-run", action="store_true")
    verify.add_argument("repo_root")
    verify.set_defaults(func=run_verify)

    add = subparsers.add_parser("add")
    add.add_argument("repo_root")
    add.add_argument("harness")
    add.set_defaults(func=run_add)

    remove = subparsers.add_parser("remove")
    remove.add_argument("repo_root")
    remove.add_argument("harness")
    remove.set_defaults(func=run_remove)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
