"""Canonical hashes, atomic checkpoints and an append-only, hash-chained journal."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from .schema import require


def canonical(value) -> str:
    return json.dumps(asdict(value) if is_dataclass(value) else value,
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(canonical(value) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def freeze_snapshot(state: dict) -> dict:
    frozen = copy.deepcopy(state)
    frozen["snapshot_hash"] = digest(state)
    return frozen


def fork_snapshot(snapshot: dict) -> dict:
    require(digest({k: v for k, v in snapshot.items() if k != "snapshot_hash"}) == snapshot["snapshot_hash"],
            "Snapshot hash mismatch")
    return copy.deepcopy(snapshot)


class Journal:
    def __init__(self, path: Path, config_hash: str):
        self.path = path
        self.config_hash = config_hash
        self.events = self.read(path)
        self.last_hash = self.events[-1]["event_hash"] if self.events else None
        self.sequence = len(self.events)

    @staticmethod
    def read(path: Path) -> list[dict]:
        events, previous = [], None
        if not path.exists():
            return events
        # Split on "\n" only: str.splitlines() also breaks at U+2028 and other
        # separators that canonical JSON (ensure_ascii=False) writes unescaped.
        lines = path.read_text(encoding="utf-8").split("\n")
        if lines[-1] == "":
            lines.pop()
        for index, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Damaged event journal at line {index}; preserve it for inspection") from exc
            event_hash = event.pop("event_hash")
            require(event["previous_hash"] == previous and digest(event) == event_hash,
                    f"Event journal hash mismatch at line {index}")
            require(event["sequence"] == index, "Event sequence mismatch")
            event["event_hash"] = event_hash
            events.append(event)
            previous = event_hash
        return events

    def append(self, kind: str, *, block_id=None, branch_id=None, phase=None,
               message_id=None, actor=None, visible_content=None, usage=None,
               status="ok", **details) -> dict:
        self.sequence += 1
        event = dict(sequence=self.sequence, kind=kind, block_id=block_id,
                     branch_id=branch_id, phase=phase, message_id=message_id, actor=actor,
                     visible_content=visible_content, timestamp=datetime.now(timezone.utc).isoformat(),
                     config_hash=self.config_hash, usage=usage, status=status,
                     previous_hash=self.last_hash, **details)
        event["event_hash"] = digest(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.last_hash = event["event_hash"]
        self.events.append(event)
        return event


class RunLock:
    """Prevent simultaneous writers; preserve a stale lock for explicit operator recovery."""
    def __init__(self, directory: Path):
        self.path = directory / ".run.lock"

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("x", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))
        except FileExistsError as exc:
            raise ValueError(f"Run locked: {self.path}. If its process has exited, remove this file explicitly.") from exc
        return self

    def __exit__(self, *_):
        self.path.unlink()
