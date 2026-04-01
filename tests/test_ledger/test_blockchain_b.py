"""Tests for the Blockchain B audit ledger."""

import tempfile
from pathlib import Path

import pytest

from voitomation.ledger.blockchain_b import AuditLedger, EventType


@pytest.fixture
def ledger(tmp_path):
    db = tmp_path / "test_audit.db"
    return AuditLedger(db_path=db)


def test_append_and_verify(ledger):
    ledger.append(EventType.VOICE_AUTH, {"user": "chris", "confidence": 0.99})
    ledger.append(EventType.INTENT, {"action": "deploy", "target": "app"})
    ledger.append(EventType.PLAN, {"steps": []})
    assert ledger.verify_chain() is True


def test_chain_links(ledger):
    e1 = ledger.append(EventType.VOICE_AUTH, {"user": "chris"})
    e2 = ledger.append(EventType.INTENT, {"action": "list"})
    assert e2.prev_hash == e1.entry_hash


def test_genesis_hash(ledger):
    e1 = ledger.append(EventType.VOICE_AUTH, {"user": "chris"})
    assert e1.prev_hash == AuditLedger.GENESIS_HASH


def test_tamper_detected(ledger, tmp_path):
    """Directly modifying the DB should break chain verification."""
    import sqlite3
    db = tmp_path / "tamper.db"
    l2 = AuditLedger(db_path=db)
    l2.append(EventType.VOICE_AUTH, {"user": "chris"})
    l2.append(EventType.INTENT, {"action": "deploy"})

    # Tamper with the first entry's payload
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE audit_log SET payload = '{\"user\": \"attacker\"}' WHERE id = 1")
    conn.commit()
    conn.close()

    assert l2.verify_chain() is False


def test_tail(ledger):
    for i in range(5):
        ledger.append(EventType.EXEC_STEP, {"step": i})
    tail = ledger.tail(3)
    assert len(tail) == 3
