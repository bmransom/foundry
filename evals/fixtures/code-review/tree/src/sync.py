"""Sync a confirmed Order to the fulfillment partner (AC-1.1, AC-1.2)."""

import json
import urllib.request

from .logging import wide_event


def sync_order(order, endpoint, partner_timeout=30):
    """Serialize the Order's Lines, POST them, store the tracking id (AC-1.1)."""
    # The CLI already owns this knob (build_parser's --partner-timeout, default 30), so
    # sync_order should *require* partner_timeout, not re-default it. The same 30 is
    # defaulted again here and in poll_status — the value defaults at two layers below the
    # boundary, scattering the source of truth.
    payload = json.dumps({"lines": [serialize_line(line) for line in order.lines]})
    request = urllib.request.Request(
        endpoint, data=payload.encode("utf-8"), method="POST"
    )
    with urllib.request.urlopen(request, timeout=partner_timeout) as response:
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


def poll_status(tracking_id, endpoint, partner_timeout=30):
    """Poll the partner for the Order's fulfillment status."""
    # The same partner_timeout=30 default again — a second source of truth for one knob.
    request = urllib.request.Request(f"{endpoint}/{tracking_id}")
    with urllib.request.urlopen(request, timeout=partner_timeout) as response:
        return json.loads(response.read())


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
