"""
Blockchain B — Append-only audit ledger.

Inc 1: SQLite hash-chain (tamper-evident, fast to build).
Inc 2: swap backend for Hyperledger Fabric.

Every entry includes:
  - event_type: what kind of event this is
  - payload:    event-specific data (dict)
  - prev_hash:  SHA-256 of the previous entry (genesis = "0" * 64)
  - entry_hash: SHA-256 of (prev_hash + event_type + json(payload) + timestamp)

The chain can be verified offline by recomputing hashes in sequence.
"""

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any

from voitomation.config import LEDGER_DB_PATH


class EventType(str, Enum):
    VOICE_AUTH      = "voice_auth"
    INTENT          = "intent"
    PLAN            = "plan"
    GOVERNANCE      = "governance"
    CONFIRMATION    = "confirmation"
    EXEC_STEP       = "exec_step"
    OUTCOME         = "outcome"
    DENIED          = "denied"
    BLOCKED         = "blocked"


@dataclass
class LedgerEntry:
    id: int
    event_type: str
    payload: dict
    timestamp: float
    prev_hash: str
    entry_hash: str


def _compute_hash(prev_hash: str, event_type: str, payload: dict, timestamp: float) -> str:
    content = f"{prev_hash}|{event_type}|{json.dumps(payload, sort_keys=True)}|{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()


class AuditLedger:
    """
    Append-only SQLite hash-chain implementing Blockchain B.

    Usage:
        ledger = AuditLedger()
        ledger.append(EventType.VOICE_AUTH, {"speaker": "chris", "confidence": 0.97})
        ledger.append(EventType.INTENT, {"action": "deploy", "target": "app-v2"})
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, db_path: Path = LEDGER_DB_PATH):
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT    NOT NULL,
                payload     TEXT    NOT NULL,
                timestamp   REAL    NOT NULL,
                prev_hash   TEXT    NOT NULL,
                entry_hash  TEXT    NOT NULL UNIQUE
            )
        """)
        self._conn.commit()

    def _last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else self.GENESIS_HASH

    def append(self, event_type: EventType, payload: dict[str, Any]) -> LedgerEntry:
        """Append an event. Returns the new entry (with its hash)."""
        prev_hash = self._last_hash()
        timestamp = time.time()
        entry_hash = _compute_hash(prev_hash, event_type.value, payload, timestamp)

        cur = self._conn.execute(
            "INSERT INTO audit_log (event_type, payload, timestamp, prev_hash, entry_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_type.value, json.dumps(payload, sort_keys=True), timestamp, prev_hash, entry_hash),
        )
        self._conn.commit()

        return LedgerEntry(
            id=cur.lastrowid,
            event_type=event_type.value,
            payload=payload,
            timestamp=timestamp,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )

    def verify_chain(self) -> bool:
        """Walk the entire chain and verify hash continuity. Returns True if intact."""
        rows = self._conn.execute(
            "SELECT event_type, payload, timestamp, prev_hash, entry_hash FROM audit_log ORDER BY id"
        ).fetchall()

        expected_prev = self.GENESIS_HASH
        for event_type, payload_str, timestamp, prev_hash, entry_hash in rows:
            if prev_hash != expected_prev:
                return False
            payload = json.loads(payload_str)
            computed = _compute_hash(prev_hash, event_type, payload, timestamp)
            if computed != entry_hash:
                return False
            expected_prev = entry_hash
        return True

    def tail(self, n: int = 10) -> list[LedgerEntry]:
        """Return the last n entries."""
        rows = self._conn.execute(
            "SELECT id, event_type, payload, timestamp, prev_hash, entry_hash "
            "FROM audit_log ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [
            LedgerEntry(id=r[0], event_type=r[1], payload=json.loads(r[2]),
                        timestamp=r[3], prev_hash=r[4], entry_hash=r[5])
            for r in reversed(rows)
        ]
