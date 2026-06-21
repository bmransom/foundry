#!/usr/bin/env python3
"""Generic append-only storage primitives shared across Foundry harness tooling.

`AppendOnlyStore` owns the domain-agnostic mechanics behind an event ledger:

- append-only ``events.jsonl`` with monotonic event ids, creation timestamps, and a
  store-id stamp; an existing event is never mutated;
- immutable hashed payloads (``write_payload`` writes if absent and refuses to
  overwrite the same path with different bytes);
- payload references by store-relative path plus SHA-256, with the path constrained to
  stay inside the store directory (no absolute path, no ``..``);
- rebuildable Tier-3 views that re-validate against any committed copy, refusing a
  rebuild when a committed view differs from the recomputed view.

Domain concerns — which event types are legal, how views are rendered, what an event
must satisfy beyond the generic guards — are supplied by subclasses through the
``_validate_append``, ``_validate_events``, and ``_render_view_bytes`` hooks.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


class AppendOnlyStore:
    """Append-only event ledger and immutable payload writer for one store."""

    #: Event field that carries the store identity; subclasses may rename it.
    store_id_field = "store_id"

    #: Fields the store stamps on every event; callers may not supply them.
    base_reserved_fields = frozenset({"event_id", "type", "created_at"})

    def __init__(self, store_dir: Path | str, store_id: str) -> None:
        self.store_dir = Path(store_dir)
        self.events_path = self.store_dir / "events.jsonl"
        if not self.events_path.is_file():
            raise FileNotFoundError(f"missing events.jsonl: {self.events_path}")
        self.store_id = store_id

    @property
    def reserved_event_fields(self) -> frozenset[str]:
        return self.base_reserved_fields | {self.store_id_field}

    @classmethod
    def init_ledger(cls, store_dir: Path | str) -> None:
        """Create an empty ledger, refusing to clobber an existing one."""
        path = Path(store_dir)
        path.mkdir(parents=True, exist_ok=True)
        events_path = path / "events.jsonl"
        if events_path.exists():
            raise FileExistsError(f"ledger already exists: {events_path}")
        events_path.write_text("", encoding="utf-8")

    def write_payload(self, relative_path: str, content: str | bytes) -> dict[str, Any]:
        payload_path = self._payload_path(relative_path)
        data = content.encode("utf-8") if isinstance(content, str) else content
        if payload_path.exists():
            if payload_path.read_bytes() != data:
                raise ValueError(f"immutable payload exists: {relative_path}")
        else:
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            payload_path.write_bytes(data)
        return {
            "path": relative_path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }

    def append_event(self, event_type: str, fields: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(fields, dict):
            raise TypeError("event fields must be a dict")
        reserved = self.reserved_event_fields.intersection(fields)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise ValueError(f"reserved event field supplied: {names}")
        supersedes = fields.get("supersedes")
        if supersedes is not None and supersedes not in self._event_ids():
            raise ValueError(f"supersedes unknown event_id: {supersedes}")
        self._validate_append(event_type, fields)

        event = {
            "event_id": self._next_event_id(),
            "type": event_type,
            "created_at": utc_now(),
            self.store_id_field: self.store_id,
            **fields,
        }
        line = json.dumps(event, sort_keys=True, separators=(",", ":"))
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
        return event

    def render_views(self) -> dict[str, Path]:
        events = self._events()
        return self._write_views(self._render_view_bytes(events))

    def rebuild(self) -> dict[str, Path]:
        events = self._events()
        self._validate_events(events)
        view_bytes = self._render_view_bytes(events)
        for name, data in view_bytes.items():
            path = self.store_dir / name
            if path.exists() and path.read_bytes() != data:
                raise ValueError(f"tier 3 view differs: {name}")
        return self._write_views(view_bytes)

    # --- domain hooks ----------------------------------------------------------

    def _validate_append(self, event_type: str, fields: dict[str, Any]) -> None:
        """Append-time guard for an incoming event. Generic store accepts any type."""

    def _validate_events(self, events: list[dict[str, Any]]) -> None:
        """Replay-time guard run before a rebuild. Generic store checks the ledger
        shape and any payload references; subclasses extend it."""
        known_event_ids: set[str] = set()
        for event in events:
            event_id = event.get("event_id")
            if not event_id:
                raise ValueError("event missing event_id")
            if event.get("supersedes") and event["supersedes"] not in known_event_ids:
                raise ValueError(f"supersedes unknown event_id: {event['supersedes']}")
            for payload in iter_payload_refs(event.get("payloads")):
                self.validate_payload_ref(payload)
            known_event_ids.add(event_id)

    def _render_view_bytes(self, events: list[dict[str, Any]]) -> dict[str, bytes]:
        """Compute the Tier-3 views. Subclasses must override to emit content."""
        raise NotImplementedError

    # --- generic mechanics -----------------------------------------------------

    def _write_views(self, view_bytes: dict[str, bytes]) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for name, data in view_bytes.items():
            path = self.store_dir / name
            path.write_bytes(data)
            paths[name] = path
        return paths

    def validate_payload_ref(self, payload: dict[str, Any]) -> None:
        relative_path = payload.get("path")
        expected_hash = payload.get("sha256")
        if not relative_path or not expected_hash:
            raise ValueError(f"payload reference missing path or sha256: {payload}")
        payload_path = self._payload_path(relative_path)
        if not payload_path.exists():
            raise ValueError(f"missing payload: {relative_path}")
        actual_hash = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"payload hash mismatch: {relative_path}")

    def _payload_path(self, relative_path: str) -> Path:
        path = PurePosixPath(relative_path)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise ValueError(
                f"payload path must stay within the store: {relative_path}"
            )
        return self.store_dir / Path(*path.parts)

    def _events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        with self.events_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid events.jsonl at line {line_number}"
                    ) from exc
        return events

    def _event_ids(self) -> set[str]:
        return {event["event_id"] for event in self._events()}

    def _next_event_id(self) -> str:
        max_number = 0
        for event in self._events():
            event_id = event.get("event_id", "")
            if isinstance(event_id, str) and event_id.startswith("e"):
                try:
                    max_number = max(max_number, int(event_id[1:]))
                except ValueError:
                    continue
        return f"e{max_number + 1:06d}"


def iter_payload_refs(value: Any):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            yield value
            return
        for child in value.values():
            yield from iter_payload_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_payload_refs(child)
