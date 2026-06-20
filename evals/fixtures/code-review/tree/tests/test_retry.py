"""Tests for the retry policy. Covers AC-2.2 only — AC-2.1 has no code to test."""

from src.retry import classify


def test_4xx_marks_sync_failed_without_retry():  # AC-2.2
    assert classify(404) == "sync-failed"
    assert classify(400) == "sync-failed"


def test_2xx_synced():
    assert classify(200) == "synced"
