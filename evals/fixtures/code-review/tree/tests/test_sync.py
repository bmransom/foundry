"""Tests for the sync engine (AC-1.1, AC-1.2)."""

import json
from unittest import mock

from src import sync


class FakeLine:
    def __init__(self, product, quantity, unit_price):
        self.product = product
        self.quantity = quantity
        self.unit_price = unit_price


class FakeOrder:
    def __init__(self):
        self.id = "order-1"
        self.lines = [FakeLine("widget", 2, 500)]
        self.tracking_id = None


def test_sync_posts_lines_and_stores_tracking_id():  # AC-1.1, AC-1.2
    order = FakeOrder()
    body = json.dumps({"tracking_id": "TRK-9"}).encode("utf-8")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return body

    with mock.patch("urllib.request.urlopen", return_value=FakeResponse()):
        tracking = sync.sync_order(order, "https://partner.example/push")

    assert tracking == "TRK-9"
    assert order.tracking_id == "TRK-9"
