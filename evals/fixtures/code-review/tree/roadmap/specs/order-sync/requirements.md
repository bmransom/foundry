# Requirements — order sync

## User stories

### US-1: Push a confirmed Order to the partner

As an operator, I want a confirmed Order pushed to the fulfillment partner so the
partner can ship it.

Acceptance criteria:

- AC-1.1 WHEN an Order is confirmed, THE SYSTEM SHALL serialize its Lines and
  POST them to the partner endpoint.
- AC-1.2 WHEN the partner returns a tracking id, THE SYSTEM SHALL store it on the
  Order and emit one Wide event for the sync.

### US-2: Retry a failed push

As an operator, I want a failed push retried with backoff so a transient partner
outage does not drop an Order.

Acceptance criteria:

- AC-2.1 WHEN a push fails with a 5xx, THE SYSTEM SHALL retry up to three times
  with exponential backoff before marking the Order sync-failed.
- AC-2.2 WHEN a push fails with a 4xx, THE SYSTEM SHALL mark the Order sync-failed
  without retrying.

### US-3: Purge the local sync cache

As an operator, I want a CLI to purge the local sync cache so a stale partner
response cannot poison a re-push.

Acceptance criteria:

- AC-3.1 WHEN the operator runs the purge command, THE SYSTEM SHALL clear every
  cached partner response.
