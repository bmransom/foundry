"""`foundry doctor` (AC-6.1/AC-6.2): five checks — config, manifest, adapters, hooks,
board — each producing zero or more findings/notes. A finding carries a fix and counts
toward the exit code; a note (fix=None) is informational only (design D3, D5).

Reuses `Config.route_for` for routing resolution, `adapters.load`/`Adapter.available`
for harness probing, and `gate.board.check` verbatim — no reimplementation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from foundry import __version__
from foundry import adapters
from foundry.config import STAGES, Config, ConfigError
from foundry.gate import board

CHECK_NAMES = ("config", "manifest", "adapters", "hooks", "board")

_PINNED_GATE_MARKER = "foundry gate"
_CHECK_FAST_MARKER = "check-fast.sh"


@dataclass(frozen=True)
class Finding:
    check: str
    defect: str
    fix: str | None = None  # None => informational note, not a failure

    @property
    def is_failure(self) -> bool:
        return self.fix is not None

    def render(self) -> str:
        if self.fix is None:
            return f"doctor: {self.check}: {self.defect}"
        return f"doctor: {self.check}: {self.defect} — fix: {self.fix}"


def _check_config(repo_root: Path) -> list[Finding]:
    path = repo_root / ".foundry" / "config.toml"
    if not path.exists():
        return [Finding("config", "no .foundry/config.toml (shipped defaults apply)")]

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        msg = str(e).replace("\n", " ")
        return [Finding(
            "config", f"{path} is malformed TOML ({msg})",
            fix=f"fix the TOML syntax in {path}",
        )]

    foundry_section = data.get("foundry", {})
    if not isinstance(foundry_section, dict):
        return [Finding(
            "config", f"{path}: 'foundry' must be a table",
            fix=f"fix the [foundry] table in {path}",
        )]

    pin = foundry_section.get("pin")
    if pin is None:
        return [Finding("config", "no [foundry].pin set; shipped defaults apply")]
    if pin != __version__:
        return [Finding(
            "config",
            f"[foundry].pin '{pin}' does not match the running CLI version '{__version__}'",
            fix=f"update {path}'s [foundry].pin to {__version__}, or install foundry {pin}",
        )]
    return []


def _check_manifest(repo_root: Path) -> tuple[list[Finding], dict | None]:
    path = repo_root / ".foundry" / "manifest.json"
    if not path.exists():
        return [Finding("manifest", "no .foundry/manifest.json (pre-bootstrap repo)")], None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        msg = str(e).replace("\n", " ")
        return [Finding(
            "manifest", f"{path} is malformed JSON ({msg})",
            fix=f"fix the JSON syntax in {path}",
        )], None

    findings: list[Finding] = []
    files = data.get("files", {})
    for rel_path, meta in files.items():
        target = repo_root / rel_path
        if not target.is_file():
            findings.append(Finding(
                "manifest", f"{rel_path} is listed in the manifest but missing on disk",
                fix=f"restore {rel_path} (`foundry update` re-materializes it), "
                    "or drop it from the manifest if the removal was intentional",
            ))
            continue
        expected = meta.get("sha256") if isinstance(meta, dict) else None
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if expected and actual != expected:
            findings.append(Finding(
                "manifest", f"{rel_path} sha256 mismatch (file changed since bootstrap/update)",
                fix=f"run `foundry update` to re-materialize {rel_path}, or if the edit is "
                    "intentional, treat it as a customized file",
            ))
    return findings, data


def _check_adapters(repo_root: Path) -> list[Finding]:
    manifest_path = repo_root / ".foundry" / "manifest.json"
    try:
        config = Config.load(repo_root)
    except ConfigError:
        return [Finding(
            "adapters",
            "skipped (config or manifest failed to parse; see the config/manifest findings)",
        )]

    routed: dict[str, list[str]] = {}
    for stage in STAGES:
        harness = config.route_for(stage).harness
        if harness:
            routed.setdefault(harness, []).append(stage)

    findings: list[Finding] = []
    manifest_present = manifest_path.is_file()
    if routed and not manifest_present:
        findings.append(Finding(
            "adapters", "manifest harness-set membership skipped (no .foundry/manifest.json)",
        ))

    for harness_name in sorted(routed):
        stages = routed[harness_name]
        if manifest_present and harness_name not in config.harnesses:
            findings.append(Finding(
                "adapters",
                f"'{harness_name}' is routed ({', '.join(stages)}) but not in the "
                "manifest's harnesses set",
                fix=f"add '{harness_name}' to .foundry/manifest.json's harnesses "
                    "(foundry bootstrap/update emits it), or route those stages to a "
                    "harness bootstrap already emitted",
            ))

        try:
            adapter = adapters.load(harness_name)
        except adapters.AdapterError as e:
            findings.append(Finding(
                "adapters", f"'{harness_name}': {e}",
                fix="use a shipped harness name (claude-code, codex) or add an adapter "
                    f"TOML for '{harness_name}'",
            ))
            continue

        if not adapter.available():
            binary = adapter.headless_command[0]
            findings.append(Finding(
                "adapters", f"'{harness_name}': command '{binary}' not found on PATH",
                fix=f"install the {harness_name} CLI so '{binary}' is on PATH, or route "
                    f"{', '.join(stages)} to a different harness",
            ))
    return findings


def _check_hooks(repo_root: Path) -> list[Finding]:
    result = subprocess.run(
        ["git", "config", "core.hooksPath"], cwd=repo_root, capture_output=True, text=True,
    )
    hooks_path = result.stdout.strip()
    findings: list[Finding] = []
    if hooks_path != ".githooks":
        findings.append(Finding(
            "hooks", f"core.hooksPath is {hooks_path!r}, not '.githooks'",
            fix="run `git config core.hooksPath .githooks` (or scripts/install-hooks.sh)",
        ))

    pre_push = repo_root / ".githooks" / "pre-push"
    if not pre_push.is_file():
        findings.append(Finding(
            "hooks", ".githooks/pre-push is missing",
            fix="create .githooks/pre-push that runs the gate (see scripts/install-hooks.sh)",
        ))
        return findings

    content = pre_push.read_text(encoding="utf-8")
    if _PINNED_GATE_MARKER in content:
        findings.append(Finding("hooks", "pre-push invokes the pinned gate (foundry gate)"))
    elif _CHECK_FAST_MARKER in content:
        findings.append(Finding(
            "hooks",
            "pre-push invokes scripts/check-fast.sh (tolerated until T13 migrates it to "
            "the pinned gate)",
        ))
    else:
        findings.append(Finding(
            "hooks",
            "pre-push invokes neither the pinned gate (`foundry gate`) nor "
            "scripts/check-fast.sh",
            fix='point .githooks/pre-push at `uvx --from "git+https://github.com/'
                'bmransom/foundry@<pin>" foundry gate` (or scripts/check-fast.sh '
                "until T13 lands)",
        ))
    return findings


def _check_board(repo_root: Path) -> list[Finding]:
    ok, lines = board.check(repo_root)
    findings: list[Finding] = []
    for line in lines:
        check_name, _, defect = line.partition(": ")
        if ok:
            findings.append(Finding(check_name, defect))
        else:
            findings.append(Finding(
                check_name, defect,
                fix="fix the flagged row in roadmap/ROADMAP.md (see the board check rules)",
            ))
    return findings


def run(repo_root: Path | str) -> tuple[bool, list[str]]:
    """Run every doctor check. Returns (ok, lines): one rendered line per
    finding/note, followed by `doctor: OK (<n> checks)` or `doctor: <n> finding(s)`.
    """
    repo_root = Path(repo_root)

    manifest_findings, _manifest_data = _check_manifest(repo_root)
    all_findings: list[Finding] = []
    all_findings += _check_config(repo_root)
    all_findings += manifest_findings
    all_findings += _check_adapters(repo_root)
    all_findings += _check_hooks(repo_root)
    all_findings += _check_board(repo_root)

    lines = [f.render() for f in all_findings]
    failures = [f for f in all_findings if f.is_failure]
    if failures:
        lines.append(f"doctor: {len(failures)} finding(s)")
    else:
        lines.append(f"doctor: OK ({len(CHECK_NAMES)} checks)")
    return not failures, lines
