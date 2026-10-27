"""Transactional append-only SQLite chain and independent verification."""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .canonical import canonical_json, sha256, strict_json
from .errors import RegistryError

REPO_ROOT = Path(__file__).resolve().parents[3]
ZERO = "0" * 64
SCHEMA = "trading-bot/registry/v1"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def location(path, repo_root=REPO_ROOT):
    path = Path(path).resolve()
    root = Path(repo_root).resolve()
    # samefile detects case aliases on case-insensitive filesystems, too.
    if path.is_relative_to(root) or any(
        p.exists() and root.exists() and p.samefile(root) for p in (path, *path.parents)
    ):
        raise RegistryError("REGISTRY_LOCATION", str(path))
    return path


def row_hash(prev_hash, body):
    return sha256(prev_hash + "\n" + body)


def verify_rows(rows, checkpoint=None):
    events, previous = [], ZERO
    for expected, row in enumerate(rows, 1):
        seq, prev, body, digest = row
        try:
            event = strict_json(body)
            if (
                seq != expected
                or not isinstance(event, dict)
                or type(event.get("seq")) is not int
                or event["seq"] != seq
                or canonical_json(event) != body
                or prev != previous
                or digest != row_hash(prev, body)
            ):
                raise ValueError("chain")
        except (ValueError, TypeError) as exc:
            raise RegistryError("REGISTRY_CHAIN_BROKEN", expected) from exc
        events.append(event)
        previous = digest
    if not events or events[0].get("type") != "registry_created":
        raise RegistryError("REGISTRY_CHAIN_BROKEN", 1)
    for event in events[1:]:
        if event.get("type") == "registry_created":
            raise RegistryError("REGISTRY_CHAIN_BROKEN", event["seq"])
    starts, finished, registered, trial_count = {}, set(), set(), 0
    for event in events:
        seq = event["seq"]
        try:
            kind = event["type"]
            if kind == "registry_created":
                if event["schema"] != SCHEMA or not isinstance(
                    event["registry_id"], str
                ):
                    raise ValueError("genesis")
                uuid.UUID(event["registry_id"])
            elif kind == "hypothesis_registered":
                if event["hypothesis_id"] in registered:
                    raise ValueError("duplicate hypothesis")
                registered.add(event["hypothesis_id"])
                variants = event["variants"]
                if not isinstance(variants, list) or not variants:
                    raise ValueError("variants")
                trial_count += len(variants)
                if (
                    type(event["trial_count_after"]) is not int
                    or event["trial_count_after"] != trial_count
                ):
                    raise ValueError("trial count")
            elif kind == "run_started":
                if type(event["run_id"]) is not int or event["run_id"] != seq:
                    raise ValueError("run id")
                supersedes = event["supersedes"]
                if supersedes is not None:
                    if type(supersedes) is not int or supersedes not in starts:
                        raise ValueError("supersedes")
                    if any(
                        event[k] != starts[supersedes][k]
                        for k in ("hypothesis_id", "variant_id", "kind")
                    ):
                        raise ValueError("supersedes identity")
                starts[seq] = event
            elif kind == "run_finished":
                run = event["run_id"]
                if (
                    type(run) is not int
                    or run not in starts
                    or run in finished
                    or event["outcome"] not in ("completed", "failed")
                ):
                    raise ValueError("finish")
                finished.add(run)
            else:
                raise ValueError("unknown type")
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise RegistryError("REGISTRY_LIFECYCLE", seq) from exc
    if checkpoint is not None:
        try:
            if set(checkpoint) != {"registry_id", "seq", "row_hash"}:
                raise ValueError("fields")
            if checkpoint["registry_id"] != events[0]["registry_id"]:
                raise RegistryError("REGISTRY_CHECKPOINT_MISMATCH", 1)
            at = checkpoint["seq"]
            if type(at) is not int or at < 1:
                raise ValueError("seq")
            if at > len(rows) or rows[at - 1][3] != checkpoint["row_hash"]:
                raise RegistryError("REGISTRY_CHECKPOINT_MISMATCH", at)
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, RegistryError):
                raise
            raise RegistryError(
                "REGISTRY_CHECKPOINT_MISMATCH", "malformed checkpoint"
            ) from exc
    return events


def read_rows(connection):
    return connection.execute(
        "SELECT seq,prev_hash,body,row_hash FROM events ORDER BY seq"
    ).fetchall()


def head(rows):
    return {
        "registry_id": strict_json(rows[0][2])["registry_id"],
        "seq": rows[-1][0],
        "row_hash": rows[-1][3],
    }


def verify_registry(path, checkpoint=None):
    path = location(path)
    try:
        # A read must never create a missing database.
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            rows = read_rows(db)
            verify_rows(rows, checkpoint)
            return head(rows)
    except sqlite3.Error as exc:
        raise RegistryError("REGISTRY_CHAIN_BROKEN", str(exc)) from exc


@contextmanager
def transaction(path, checkpoint=None, *, repo_root=REPO_ROOT):
    path = location(path, repo_root)
    db = None
    try:
        db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=30)
        db.execute("BEGIN IMMEDIATE")
        rows = read_rows(db)
        events = verify_rows(rows, checkpoint)
        yield db, events
        db.commit()
    except sqlite3.Error as exc:
        raise RegistryError("REGISTRY_WRITE_FAILED", str(exc)) from exc
    finally:
        if db is not None:
            db.close()  # Rolls back an uncommitted append on any exception.


def append_event(db, event):
    rows = read_rows(db)
    seq = len(rows) + 1
    event = {**event, "seq": seq}
    if event["type"] == "run_started":
        event["run_id"] = seq
    prev = rows[-1][3] if rows else ZERO
    body = canonical_json(event)
    row = (seq, prev, body, row_hash(prev, body))
    verify_rows([*rows, row])
    db.execute("INSERT INTO events VALUES (?,?,?,?)", row)
    return event


def init_registry(path, *, clock=utc_now, repo_root=REPO_ROOT):
    path = location(path, repo_root)
    # Exclusive creation prevents accidentally replacing any existing registry.
    try:
        with path.open("xb"):
            pass
    except OSError as exc:
        raise RegistryError("REGISTRY_WRITE_FAILED", str(exc)) from exc
    try:
        with sqlite3.connect(path) as db:
            db.executescript("""
                CREATE TABLE events (seq INTEGER PRIMARY KEY, prev_hash TEXT NOT NULL,
                                     body TEXT NOT NULL, row_hash TEXT NOT NULL);
                CREATE TRIGGER no_update BEFORE UPDATE ON events BEGIN
                    SELECT RAISE(ABORT, 'append-only registry'); END;
                CREATE TRIGGER no_delete BEFORE DELETE ON events BEGIN
                    SELECT RAISE(ABORT, 'append-only registry'); END;
            """)
            db.execute("BEGIN IMMEDIATE")
            append_event(
                db,
                {
                    "type": "registry_created",
                    "registry_id": str(uuid.uuid4()),
                    "schema": SCHEMA,
                    "timestamp_utc": clock(),
                },
            )
        return verify_registry(path)
    except (sqlite3.Error, OSError) as exc:
        raise RegistryError("REGISTRY_WRITE_FAILED", str(exc)) from exc
