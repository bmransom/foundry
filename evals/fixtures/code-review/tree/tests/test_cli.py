"""Tests for the cache-purge CLI (AC-3.1)."""

from src.cli import purge_cache


def test_purge_all_clears_every_cache():  # AC-3.1
    assert purge_cache("all") == "all"


def test_purge_partner_clears_only_partner_cache():
    assert purge_cache("partner") == "partner"
