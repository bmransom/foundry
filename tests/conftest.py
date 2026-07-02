"""Shared pytest fixtures. Exposes the repo fixture factory (tests/fixtures/repos)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "fixtures" / "repos"))

from doctor_fixture import make_doctor_repo  # noqa: E402
from factory import branch_exists, head_sha, make_repo  # noqa: E402
from gate_fixture import make_gate_fixture  # noqa: E402
from migration_fixtures import (  # noqa: E402
    make_card_ids_repo,
    make_conv1_chain_repo,
    make_harness_repo,
    make_legacy_repo,
    make_okf_repo,
)
from pinned_run_fixture import make_pinned_run_repo  # noqa: E402


@pytest.fixture
def repo_factory():
    return make_repo


@pytest.fixture
def git_probes():
    return {"head_sha": head_sha, "branch_exists": branch_exists}


@pytest.fixture
def gate_fixture():
    return make_gate_fixture


@pytest.fixture
def doctor_fixture():
    return make_doctor_repo


@pytest.fixture
def pinned_run_fixture():
    return make_pinned_run_repo


@pytest.fixture
def okf_fixture():
    return make_okf_repo


@pytest.fixture
def harness_fixture():
    return make_harness_repo


@pytest.fixture
def card_ids_fixture():
    return make_card_ids_repo


@pytest.fixture
def conv1_chain_fixture():
    return make_conv1_chain_repo


@pytest.fixture
def legacy_fixture():
    return make_legacy_repo
