"""Sync a confirmed Order to the fulfillment partner (AC-1.1, AC-1.2)."""

import json
import urllib.request

from .logging import wide_event


def sync_order(order, endpoint):
    """Serialize the Order's Lines, POST them, store the tracking id (AC-1.1)."""
    payload = json.dumps({"lines": [serialize_line(line) for line in order.lines]})
    request = urllib.request.Request(
        endpoint, data=payload.encode("utf-8"), method="POST"
    )
    with urllib.request.urlopen(request) as response:
        body = json.loads(response.read())
    tracking_id = body["tracking_id"]
    order.tracking_id = tracking_id

    # AC-1.2: one canonical Wide event for the sync.
    wide_event(
        "order.synced",
        order_id=order.id,
        line_count=len(order.lines),
        tracking_id=tracking_id,
    )
    # DEBT: a raw print beside the Wide event for the same unit of work. The
    # Wide event already carries these fields; this duplicate line is logging mix.
    print(f"sync complete for order {order.id} -> {tracking_id}")
    return tracking_id


def serialize_line(line):
    """Serialize one Line for the partner payload.

    The partner's shipping job consumes this payload directly, so the field names
    must match the partner contract exactly.
    """
    return {
        "product": line.product,
        "quantity": line.quantity,
        "unit_price": line.unit_price,
    }
