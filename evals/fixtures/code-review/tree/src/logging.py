"""The canonical structured logger: one Wide event per unit of work."""

import json
import sys


def wide_event(name, **fields):
    """Emit one structured Wide event line — the only logging a production path does."""
    record = {"event": name}
    record.update(fields)
    sys.stderr.write(json.dumps(record) + "\n")
