"""Discrimination tests (T11, tasks.md; AC-8.2 posture): each seeded defect must make
the gate suite FAIL end-to-end, and the clean fixture must PASS end-to-end with
`gate: PASS` as the last line — never green-ness alone.
"""

from foundry.gate import suite


def test_clean_fixture_passes_end_to_end(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path)
    ok, lines = suite.run(repo)
    assert ok is True
    assert lines[-1] == "gate: PASS"


def test_board_defect_fails_the_suite(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path, board_defect=True)
    ok, lines = suite.run(repo)
    assert ok is False
    assert lines[-1] == "gate: FAIL"
    assert any("claimable card missing Id" in line for line in lines)


def test_prose_defect_fails_the_suite(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path, prose_defect=True)
    ok, lines = suite.run(repo)
    assert ok is False
    assert lines[-1] == "gate: FAIL"
    assert any("banned filler phrase" in line for line in lines)


def test_knowledge_defect_fails_the_suite(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path, knowledge_defect=True)
    ok, lines = suite.run(repo)
    assert ok is False
    assert lines[-1] == "gate: FAIL"
    assert any("invalid type 'bogus'" in line for line in lines)


def test_failing_gate_command_fails_the_suite(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path, gate_command="python3 -c \"import sys; sys.exit(1)\"")
    ok, lines = suite.run(repo)
    assert ok is False
    assert lines[-1] == "gate: FAIL"
    assert any("command failed" in line for line in lines)


def test_passing_gate_command_keeps_the_suite_green(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path, gate_command="python3 -c \"import sys; sys.exit(0)\"")
    ok, lines = suite.run(repo)
    assert ok is True
    assert lines[-1] == "gate: PASS"
