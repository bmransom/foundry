"""Extra order-sync helpers.

Fixture note: this module seeds calibration DECOYS (D4-D7) — a well-calibrated agent
reviewer flags NONE of these. Each is grounded in the order-sync spec; flagging one is
the agent-review failure mode (false positive) the calibration guardrails forbid.
"""


# D4 (style, AC-14.6): a camelCase name is a linter/formatter concern, not a review
# finding — the repo's deterministic tools own naming style.
def buildPayload(order):
    return {"id": order.id, "lines": [line.sku for line in order.lines]}


# D5 (spec-conforming, AC-15.1): AC-2.2 says a 4xx marks the Order sync-failed WITHOUT
# retrying. This conforms exactly; "you should retry the 4xx" is not a defect.
def handle_4xx(order):
    order.status = "sync-failed"  # AC-2.2: no retry on a 4xx


# D6 (invented requirement, AC-15.2): AC-3.1 requires purge to clear the cache; it does
# NOT require a confirmation prompt. "Add a confirmation step" invents a requirement.
def purge_local_cache(cache):
    cache.clear()


# D7 (read context, AC-14.5): per_order_cost looks like a divide-by-zero, but split_bill
# guards count > 0 before calling it — a diff-local reading is a false positive.
def per_order_cost(total, count):
    return total / count


def split_bill(total, count):
    if count <= 0:
        raise ValueError("count must be positive")  # guards per_order_cost
    return per_order_cost(total, count)
