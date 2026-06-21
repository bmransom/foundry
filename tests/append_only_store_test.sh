#!/usr/bin/env bash
# Unit checks for the shared AppendOnlyStore primitives.
# Hermetic: must pass with codex/claude/tmux absent (restricted PATH).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODULE="$REPO/plugins/foundry/scripts/append_only_store.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$MODULE" ] || fail "missing append_only_store.py"

fixture="$(mktemp -d)"
trap 'rm -rf "$fixture"' EXIT

python3 - "$MODULE" "$fixture" <<'PY'
import importlib.util
import json
import pathlib
import sys

module_path = pathlib.Path(sys.argv[1])
fixture = pathlib.Path(sys.argv[2])

spec = importlib.util.spec_from_file_location("append_only_store", module_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

AppendOnlyStore = module.AppendOnlyStore


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def assert_raises(fragment, func):
    try:
        func()
    except (ValueError, FileExistsError) as exc:
        assert fragment in str(exc), f"expected {fragment!r} in {str(exc)!r}"
    else:
        raise AssertionError(f"expected failure containing {fragment!r}")


class DemoStore(AppendOnlyStore):
    """Minimal concrete store: views echo the event ids in deterministic order."""

    def _render_view_bytes(self, events):
        ids = "\n".join(event["event_id"] for event in events)
        return {
            "view.txt": (ids + "\n").encode("utf-8"),
            "count.txt": (str(len(events)) + "\n").encode("utf-8"),
        }


def make_store(name):
    store_dir = fixture / name
    AppendOnlyStore.init_ledger(store_dir)
    return DemoStore(store_dir, name)


def read_lines(store):
    with store.events_path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# --- append-only ordering: monotonic ids, store stamp, never mutate ----------
store = make_store("ordering")
first = store.append_event("alpha", {"value": 1})
second = store.append_event("beta", {"value": 2})
third = store.append_event("alpha", {"value": 3, "supersedes": first["event_id"]})

assert_equal(first["event_id"], "e000001", "first id")
assert_equal(second["event_id"], "e000002", "second id")
assert_equal(third["event_id"], "e000003", "third id")
assert_equal(first["store_id"], "ordering", "store id stamped")
assert_equal(third["supersedes"], "e000001", "supersedes recorded")
assert "created_at" in first, "created_at stamped"

ledger = read_lines(store)
assert_equal([event["event_id"] for event in ledger], ["e000001", "e000002", "e000003"], "monotonic ledger")
# Reopening continues the sequence; existing events are untouched.
before = store.events_path.read_bytes()
reopened = DemoStore(store.store_dir, "ordering")
fourth = reopened.append_event("beta", {"value": 4})
assert_equal(fourth["event_id"], "e000004", "id continues after reopen")
assert before == store.events_path.read_bytes()[: len(before)], "existing events not mutated"

# A reserved field may not be supplied by the caller.
assert_raises("reserved event field supplied", lambda: store.append_event("alpha", {"event_id": "e999999"}))
assert_raises("reserved event field supplied", lambda: store.append_event("alpha", {"store_id": "x"}))
# supersedes must reference an existing event.
assert_raises("supersedes unknown event_id", lambda: store.append_event("alpha", {"supersedes": "e123456"}))
# init_ledger refuses to clobber an existing ledger.
assert_raises("ledger already exists", lambda: AppendOnlyStore.init_ledger(store.store_dir))

# --- immutable payloads: refuse on different bytes, allow identical rewrite ---
payload_store = make_store("payloads")
ref = payload_store.write_payload("nested/dir/body.md", "hello\n")
assert_equal(ref["path"], "nested/dir/body.md", "payload path echoed")
assert_equal(ref["bytes"], len(b"hello\n"), "payload byte count")
import hashlib

assert_equal(ref["sha256"], hashlib.sha256(b"hello\n").hexdigest(), "payload hash")
# Rewriting the same bytes is a no-op that returns the same ref.
again = payload_store.write_payload("nested/dir/body.md", "hello\n")
assert_equal(again, ref, "identical rewrite returns same ref")
# Rewriting different bytes at the same path is refused.
assert_raises("immutable payload exists", lambda: payload_store.write_payload("nested/dir/body.md", "changed\n"))

# --- path containment: no absolute path, no .., no empty -----------------------
assert_raises("stay within the store", lambda: payload_store.write_payload("/etc/passwd", "x"))
assert_raises("stay within the store", lambda: payload_store.write_payload("../escape.md", "x"))
assert_raises("stay within the store", lambda: payload_store.write_payload("nested/../../escape.md", "x"))
assert_raises("stay within the store", lambda: payload_store.write_payload("", "x"))

# --- rebuild hash re-validation -----------------------------------------------
rebuild_store = make_store("rebuild")
body = rebuild_store.write_payload("turns/final.md", "final body\n")
rebuild_store.append_event("alpha", {"payloads": {"final": body}})
rebuild_store.append_event("beta", {"value": 7})

first_views = rebuild_store.rebuild()
view_bytes = {name: path.read_bytes() for name, path in first_views.items()}
assert_equal(view_bytes["count.txt"], b"2\n", "view reflects event count")

# Rebuild is deterministic and byte-identical.
for name in view_bytes:
    (rebuild_store.store_dir / name).unlink()
rebuild_store.render_views()
second_views = {name: (rebuild_store.store_dir / name).read_bytes() for name in view_bytes}
assert_equal(second_views, view_bytes, "views rebuild byte-identically")

# A committed view that differs from the recompute refuses the rebuild.
(rebuild_store.store_dir / "view.txt").write_bytes(b"tampered\n")
assert_raises("tier 3 view differs", rebuild_store.rebuild)
# Restore the view so later payload checks are isolated.
rebuild_store.render_views()

# Corrupting a referenced payload refuses the rebuild via hash re-validation.
(rebuild_store.store_dir / "turns/final.md").write_text("corrupted\n", encoding="utf-8")
assert_raises("payload hash mismatch", rebuild_store.rebuild)

# Removing a referenced payload refuses the rebuild.
(rebuild_store.store_dir / "turns/final.md").unlink()
assert_raises("missing payload", rebuild_store.rebuild)

# --- generic store rejects an opaque view contract by default ------------------
plain_dir = fixture / "plain"
AppendOnlyStore.init_ledger(plain_dir)
plain = AppendOnlyStore(plain_dir, "plain")
plain.append_event("alpha", {"value": 1})
try:
    plain.render_views()
except NotImplementedError:
    pass
else:
    raise AssertionError("base store must not render views")

print("OK")
PY

echo "append_only_store_test: PASS"
