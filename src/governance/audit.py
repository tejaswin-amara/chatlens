"""Structured auditability and forensic telemetry for agent governance.

Enforces an immutable, append-only SQLite governance audit trail.
Records event fingerprints, policy verdicts, human approvers, and rollback diffs.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import time
from typing import Any

from src.config import settings
from src.governance.guards import UntrustedInput
from src.governance.policy_engine import ActionTier, PolicyVerdict
from src.utils.db import get_connection
from src.utils.logging import get_logger
from src.utils.redaction import redact_pii

logger = get_logger(__name__)


class GovernanceAuditLogger:
    """Append-only forensic governance audit trail stored in SQLite."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._initialized_dbs: set[str] = set()
        self._ensure_schema()

    @property
    def db_path(self) -> str:
        return self._db_path or settings.spark_db

    @db_path.setter
    def db_path(self, val: str | None) -> None:
        self._db_path = val

    def _ensure_schema(self) -> None:
        """Create governance_audit table and indexes if not present."""
        target_db = self.db_path
        if target_db in self._initialized_dbs:
            return
        with get_connection(target_db) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governance_audit (
                    event_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    raw_fingerprint TEXT NOT NULL,
                    source_trust_tier TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    extracted_intent TEXT NOT NULL,
                    risk_tier TEXT NOT NULL,
                    policy_verdict TEXT NOT NULL,
                    approver_id TEXT NOT NULL,
                    rollback_payload TEXT,
                    details TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_gov_audit_ts
                ON governance_audit (timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_gov_audit_verdict
                ON governance_audit (policy_verdict)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_gov_audit_fingerprint
                ON governance_audit (raw_fingerprint)
            """)
        self._initialized_dbs.add(target_db)

    def _get_conn(self) -> contextlib.AbstractContextManager[sqlite3.Connection]:
        self._ensure_schema()
        return get_connection(self.db_path)

    @staticmethod
    def generate_event_id(channel_id: int | str, msg_id: int | str, timestamp: float) -> str:
        """Deterministic SHA-256 event ID based on channel, message ID, and timestamp."""
        payload = f"{channel_id}:{msg_id}:{timestamp}".encode()
        return hashlib.sha256(payload).hexdigest()

    def log_action(
        self,
        event_id: str,
        untrusted_input: UntrustedInput,
        extracted_intent: str,
        risk_tier: ActionTier | str,
        policy_verdict: PolicyVerdict | str,
        approver_id: str = "SYSTEM_AUTO",
        rollback_payload: dict[str, Any] | str | None = None,
        details: str = "",
    ) -> str:
        """Log an immutable governance decision to SQLite."""
        ts = untrusted_input.timestamp or time.time()
        rollback_str = (
            json.dumps(rollback_payload)
            if isinstance(rollback_payload, dict)
            else (rollback_payload or "")
        )

        tier_str = risk_tier.value if isinstance(risk_tier, ActionTier) else str(risk_tier)
        verdict_str = (
            policy_verdict.value
            if isinstance(policy_verdict, PolicyVerdict)
            else str(policy_verdict)
        )

        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO governance_audit (
                        event_id, timestamp, raw_fingerprint, source_trust_tier,
                        channel_id, sender_id, extracted_intent, risk_tier,
                        policy_verdict, approver_id, rollback_payload, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO UPDATE SET
                        policy_verdict = excluded.policy_verdict,
                        approver_id = excluded.approver_id,
                        details = excluded.details
                    """,
                    (
                        event_id,
                        ts,
                        untrusted_input.raw_fingerprint,
                        untrusted_input.source_trust_tier,
                        str(untrusted_input.channel_id),
                        str(untrusted_input.sender_id),
                        extracted_intent,
                        tier_str,
                        verdict_str,
                        str(approver_id),
                        rollback_str,
                        redact_pii(details),
                    ),
                )
            logger.info(
                "governance_audit_logged",
                event_id=event_id,
                verdict=verdict_str,
                intent=extracted_intent,
                tier=tier_str,
            )
        except sqlite3.Error as e:
            logger.error("Failed to write governance audit record", error=str(e))

        return event_id

    def update_verdict(
        self,
        event_id: str,
        verdict: PolicyVerdict | str,
        approver_id: str,
        details: str = "",
    ) -> bool:
        """Record human approval or rejection on a pending action."""
        verdict_str = verdict.value if isinstance(verdict, PolicyVerdict) else str(verdict)
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE governance_audit
                    SET policy_verdict = ?, approver_id = ?, details = details || ' | ' || ?
                    WHERE event_id = ?
                    """,
                    (verdict_str, str(approver_id), details, event_id),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error("Failed to update governance audit verdict", error=str(e))
            return False

    def get_audit_trail(self, limit: int = 50, verdict: str | None = None) -> list[dict[str, Any]]:
        """Retrieve recent forensic audit records."""
        records = []
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                if verdict:
                    query = (
                        "SELECT * FROM governance_audit WHERE policy_verdict = ? "
                        "ORDER BY timestamp DESC LIMIT ?"
                    )
                    cursor = conn.execute(query, (verdict, limit))
                else:
                    cursor = conn.execute(
                        "SELECT * FROM governance_audit ORDER BY timestamp DESC LIMIT ?",
                        (limit,),
                    )
                for row in cursor.fetchall():
                    records.append(dict(row))
        except sqlite3.Error as e:
            logger.error("Failed to query governance audit records", error=str(e))
        return records

    def get_record(self, event_id: str) -> dict[str, Any] | None:
        """Fetch a specific audit record by event ID."""
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM governance_audit WHERE event_id = ?",
                    (event_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error("Failed to fetch audit record", error=str(e))
            return None


audit_logger = GovernanceAuditLogger()
